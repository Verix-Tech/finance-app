#!/usr/bin/env python3
"""
Simple test tasks for Celery testing.
"""

from celery import shared_task

@shared_task
def simple_test_task():
    """A simple test task that just returns a message."""
    return "Hello from Celery test task!"

@shared_task
def echo_task(message):
    """A task that echoes back the input message."""
    return f"Echo: {message}" 