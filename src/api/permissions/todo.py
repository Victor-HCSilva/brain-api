from rest_framework import permissions


class IsOwnerOrFolderOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.pode_editar(request.user)
        return obj.pode_excluir(request.user) or obj.pode_editar(request.user)


class IsFolderOwnerOrCollaborator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "DELETE":
            return obj.pode_excluir(request.user)
        if obj.user == request.user:
            return True
        return obj.pode_editar(request.user)
