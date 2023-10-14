from rest_framework import serializers
from .models import BoardCollectionDB, BoardDB, Post


class BoardCollectionDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardCollectionDB
        fields = "__all__"


class BoardDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardDB
        fields = "__all__"


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = "__all__"
