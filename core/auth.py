# core/auth.py
"""Simple role detection - no complex auth, just UI mode selection"""
from __future__ import annotations
import streamlit as st
from .models import Role, Permissions
from .calculations import get_role_permissions


def init_role_state():
    """Initialize role in session state"""
    if "user_role" not in st.session_state:
        st.session_state.user_role = Role.HOTELIER  # Default to hotelier view


def get_current_role() -> Role:
    """Get current user role from session state"""
    init_role_state()
    return st.session_state.user_role


def get_current_permissions() -> Permissions:
    """Get permissions for current role"""
    return get_role_permissions(get_current_role())


def role_selector() -> Role:
    """UI component to switch roles (sidebar)"""
    init_role_state()
    
    role_labels = {
        Role.ADMIN: "👑 Admin (Chamba Digital)",
        Role.HOTELIER: "🏨 Hotelier (Peña Linda)",
    }
    
    current = get_current_role()
    selected = st.sidebar.selectbox(
        "Modo de vista",
        options=list(Role),
        format_func=lambda r: role_labels[r],
        index=list(Role).index(current),
        key="role_selector"
    )
    
    if selected != current:
        st.session_state.user_role = selected
        st.rerun()
    
    return selected


def require_permission(permission: str) -> bool:
    """Check if current role has permission, show message if not"""
    perms = get_current_permissions()
    if not getattr(perms, permission, False):
        st.warning(f"🔒 Esta función requiere permisos de administrador")
        return False
    return True