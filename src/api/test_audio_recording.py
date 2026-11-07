from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from main.models import AudioRecording, Folder, Todo

User = get_user_model()


class AudioRecordingAPITests(APITestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.owner = User.objects.create_user(username="audio_owner", password="test-pass")
        self.collaborator = User.objects.create_user(username="audio_collaborator", password="test-pass")
        self.other = User.objects.create_user(username="audio_other", password="test-pass")
        self.folder = Folder.objects.create(user=self.owner, name="Pasta de áudios")
        self.todo = Todo.objects.create(user=self.owner, titulo="Aula", is_active=True)
        self.todo.colaboradores.add(self.collaborator)

    def upload_audio(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:audio-recording-list"),
            {
                "titulo": "Resumo da aula",
                "audio": SimpleUploadedFile(
                    "resumo.webm", b"fake audio data", content_type="audio/webm"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_owner_can_upload_audio_and_it_appears_in_their_library(self):
        created = self.upload_audio()

        self.assertEqual(created["titulo"], "Resumo da aula")
        self.assertEqual(created["stream_url"], f"/api/audio-recordings/{created['id']}/stream/")
        library = self.client.get(reverse("api:audio-recording-list"))
        self.assertEqual(len(library.data["results"]), 1)

    def test_collaborator_can_stream_linked_audio_but_not_see_owners_library(self):
        created = self.upload_audio()
        link_response = self.client.post(
            reverse("api:audio-linker-list"),
            {"todo": self.todo.pk, "audio": created["id"]},
            format="json",
        )
        self.assertEqual(link_response.status_code, 201)
        self.client.force_authenticate(user=self.collaborator)

        links = self.client.get(reverse("api:audio-linker-list"), {"todo": self.todo.pk})
        library = self.client.get(reverse("api:audio-recording-list"))
        stream = self.client.get(
            reverse("api:audio-recording-stream", kwargs={"pk": created["id"]})
        )

        self.assertEqual(links.status_code, 200)
        self.assertEqual(len(links.data["results"]), 1)
        self.assertEqual(library.status_code, 200)
        self.assertEqual(library.data["results"], [])
        self.assertEqual(stream.status_code, 200)
        self.assertEqual(stream["Content-Type"], "audio/webm")
        unlink = self.client.delete(
            reverse("api:audio-linker-detail", kwargs={"pk": links.data["results"][0]["id"]})
        )
        self.assertEqual(unlink.status_code, 404)

    def test_user_cannot_link_audio_to_an_inaccessible_task(self):
        self.client.force_authenticate(user=self.other)
        upload = self.client.post(
            reverse("api:audio-recording-list"),
            {
                "titulo": "Gravação particular",
                "audio": SimpleUploadedFile("privado.ogg", b"audio", content_type="audio/ogg"),
            },
            format="multipart",
        )

        response = self.client.post(
            reverse("api:audio-linker-list"),
            {"todo": self.todo.pk, "audio": upload.data["id"]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AudioRecording.objects.get(pk=upload.data["id"]).vinculos_todo.exists())

    def test_upload_rejects_non_audio_file_extensions(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("api:audio-recording-list"),
            {
                "titulo": "Arquivo não permitido",
                "audio": SimpleUploadedFile("payload.txt", b"not audio", content_type="text/plain"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("audio", response.data)

    def test_audio_can_be_stored_in_a_folder_and_filtered_by_folder(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            reverse("api:audio-recording-list"),
            {
                "titulo": "Gravação organizada",
                "folder": self.folder.pk,
                "audio": SimpleUploadedFile("aula.mp3", b"audio", content_type="audio/mpeg"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["folder"], self.folder.pk)
        self.assertEqual(response.data["folder_name"], self.folder.name)
        filtered = self.client.get(reverse("api:audio-recording-list"), {"folder": self.folder.pk})
        self.assertEqual(len(filtered.data["results"]), 1)

    def test_audio_can_be_created_without_a_task_or_folder_and_updated_later(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            reverse("api:audio-recording-list"),
            {
                "titulo": "Gravação independente",
                "audio": SimpleUploadedFile("independente.wav", b"audio", content_type="audio/wav"),
            },
            format="multipart",
        )

        self.assertEqual(created.status_code, 201)
        self.assertIsNone(created.data["folder"])
        self.assertFalse(AudioRecording.objects.get(pk=created.data["id"]).vinculos_todo.exists())

        updated = self.client.patch(
            reverse("api:audio-recording-detail", kwargs={"pk": created.data["id"]}),
            {"folder": self.folder.pk},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["folder"], self.folder.pk)
