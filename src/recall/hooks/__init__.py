"""Recall memory persistence hooks for Claude Code.

Thin coordination hooks that inject instructions via systemMessage/additionalContext.
Claude makes the actual MCP tool calls. All hooks use stdlib only and complete in <500ms.
"""
