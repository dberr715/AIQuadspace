from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from .models import ChatMessage, EmailUser, ChatThread
import json
from django.db.models import F
import re

from django.db import transaction
from django.contrib import messages
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser


import logging

logger = logging.getLogger(__name__)


def parse_thread_identifier(thread_identifier):
    try:
        email, thread_id = thread_identifier.rsplit("-", 1)
        return email, int(thread_id)
    except ValueError:
        return thread_identifier, None


@api_view(["POST"])
def register(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if EmailUser.objects.filter(email=email).exists():
        return Response(
            {"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST
        )
    user = EmailUser.objects.create_user(email=email, password=password)
    return Response(
        {"message": "User created successfully"}, status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
def login_user(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not EmailUser.objects.filter(email=email).exists():
        return Response(
            {"error": "Email does not exist in our system."},
            status=status.HTTP_404_NOT_FOUND,
        )

    user = authenticate(email=email, password=password)
    if user is not None:
        if user.is_active:
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        else:
            return Response(
                {"error": "User account is inactive."}, status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {"error": "Password is incorrect."}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["POST"])
def token_obtain_pair(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not password:
        return Response(
            {"password": ["This field may not be blank."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(email=email, password=password)
    if not user:
        return Response(
            {"detail": "No active account found with the given credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )


@api_view(["GET"])
def check_admin(request):
    if request.user.is_authenticated:
        return Response({"isAdmin": request.user.is_admin})
    return Response({"isAdmin": False}, status=status.HTTP_403_FORBIDDEN)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_thread_ids(request):
    threads_by_user = {}
    for user in EmailUser.objects.all():
        threads = ChatThread.objects.filter(user=user)
        threads_by_user[user.email] = [
            thread.get_thread_identifier() for thread in threads
        ]
    return JsonResponse(threads_by_user, safe=False)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_chat_thread(request):
    user = request.user
    new_thread = ChatThread.objects.create(user=user)
    new_thread_identifier = str(new_thread.id)
    return JsonResponse(
        {"threadIdentifier": new_thread_identifier}, status=status.HTTP_201_CREATED
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_chat_history(request, thread_id):
    try:
        thread = ChatThread.objects.get(id=thread_id)
        chat_messages = ChatMessage.objects.filter(thread=thread).order_by("timestamp")
        data = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in chat_messages
        ]
        return JsonResponse(data, safe=False)
    except ChatThread.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Thread not found"}, status=404
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_chat_message(request):
    try:
        data = request.data
        thread_id = data.get("threadIdentifier")
        content = data.get("content")
        role = data.get("role")

        if not thread_id or not content or not role:
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"}, status=400
            )

        thread = ChatThread.objects.get(id=thread_id)
        user = thread.user

        ChatMessage.objects.create(user=user, role=role, content=content, thread=thread)

        return JsonResponse({"status": "success"})

    except ChatThread.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Thread not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return JsonResponse(
            {"status": "error", "message": "Internal server error"}, status=500
        )
