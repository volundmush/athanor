from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import BoardCollectionDB, BoardDB, Post
from .serializers import BoardCollectionDBSerializer, BoardDBSerializer, PostSerializer


class BoardCollectionViewSet(viewsets.ViewSet):
    pass
