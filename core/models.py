# core/models.py
"""Pydantic models for type-safe data handling"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TransactionSource(str, Enum):
    """Source of a transaction"""
    SIRVOY = "sirvoy"
    IZIPAY_ONLINE = "izipay_online"
    CULQI_ONLINE = "culqi_online"
    OPENPAY_ONLINE = "openpay_online"
    IZIPAY_POS = "izipay_pos"
    CULQI_POS = "culqi_pos"
    OPENPAY_POS = "openpay_pos"
    COSTO_FB = "costo_fb"
    COSTO_SIRVOY = "costo_sirvoy"
    COSTO_ASISTENTE = "costo_asistente"
    COSTO_EXTRA = "costo_extra"
    ABONO_CHAMBA = "abono_chamba"
    SALDO_BASE = "saldo_base"
    
    @property
    def display_name(self) -> str:
        names = {
            TransactionSource.SIRVOY: "Sirvoy",
            TransactionSource.IZIPAY_ONLINE: "Izipay Web",
            TransactionSource.CULQI_ONLINE: "Culqi Web",
            TransactionSource.OPENPAY_ONLINE: "Openpay Web",
            TransactionSource.IZIPAY_POS: "Izipay POS",
            TransactionSource.CULQI_POS: "Culqi POS",
            TransactionSource.OPENPAY_POS: "Openpay POS",
            TransactionSource.COSTO_FB: "Facebook Ads",
            TransactionSource.COSTO_SIRVOY: "Sirvoy Software",
            TransactionSource.COSTO_ASISTENTE: "Asistente Comercial",
            TransactionSource.COSTO_EXTRA: "Costos Extra",
            TransactionSource.ABONO_CHAMBA: "Abono Chamba Digital",
            TransactionSource.SALDO_BASE: "Saldo Base",
        }
        return names.get(self, self.value)
    
    @property
    def is_platform_online(self) -> bool:
        return self in (
            TransactionSource.IZIPAY_ONLINE,
            TransactionSource.CULQI_ONLINE,
            TransactionSource.OPENPAY_ONLINE,
        )
    
    @property
    def is_platform_pos(self) -> bool:
        return self in (
            TransactionSource.IZIPAY_POS,
            TransactionSource.CULQI_POS,
            TransactionSource.OPENPAY_POS,
        )
    
    @property
    def is_cost(self) -> bool:
        return self in (
            TransactionSource.COSTO_FB,
            TransactionSource.COSTO_SIRVOY,
            TransactionSource.COSTO_ASISTENTE,
            TransactionSource.COSTO_EXTRA,
        )
    
    @property
    def is_abono(self) -> bool:
        return self == TransactionSource.ABONO_CHAMBA


class TransactionType(str, Enum):
    VENTA = "venta"
    COSTO = "costo"
    ABONO = "abono"
    SALDO_INICIAL = "saldo_inicial"


class InvoiceType(str, Enum):
    COMISION = "comision"
    COSTO_OPERATIVO = "costo_operativo"
    ABONO_RECIBIDO = "abono_recibido"
    SALDO_INICIAL = "saldo_inicial"


class InvoiceStatus(str, Enum):
    PAGADA = "pagada"
    VENCIDA = "vencida"
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"


class Role(str, Enum):
    ADMIN = "admin"
    HOTELIER = "hotelier"


class Permissions(BaseModel):
    ventas: bool = True
    costos: bool = False
    abonos: bool = True
    pos_manual: bool = True
    historial: bool = True
    config: bool = False


class Transaction(BaseModel):
    """Normalized transaction model"""
    id: str = ""
    source: TransactionSource = TransactionSource.SIRVOY
    tx_type: TransactionType = TransactionType.VENTA
    amount: Decimal = Decimal("0")
    currency: str = "PEN"
    method: str = ""
    reference: str = ""
    fecha: datetime
    fecha_pe: Optional[datetime] = None  # Peru timezone
    commission: Decimal = Decimal("0")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    hash: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_sale(self) -> bool:
        return self.tx_type == TransactionType.VENTA
    
    @property
    def is_cost(self) -> bool:
        return self.tx_type == TransactionType.COSTO
    
    @property
    def is_abono(self) -> bool:
        return self.tx_type == TransactionType.ABONO
    
    @property
    def is_saldo_inicial(self) -> bool:
        return self.tx_type == TransactionType.SALDO_INICIAL


class Invoice(BaseModel):
    """Invoice model (Chamba → Peña Linda billing)"""
    id: str = ""
    invoice_type: InvoiceType = InvoiceType.COSTO_OPERATIVO
    category: str = ""
    amount: Decimal = Decimal("0")
    currency: str = "PEN"
    fecha_emision: datetime
    fecha_vencimiento: Optional[datetime] = None
    estado_qb: InvoiceStatus = InvoiceStatus.PENDIENTE
    qb_ref: str = ""
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None
    hash: str = ""
    origen_importacion: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_comision(self) -> bool:
        return self.invoice_type == InvoiceType.COMISION
    
    @property
    def is_costo(self) -> bool:
        return self.invoice_type == InvoiceType.COSTO_OPERATIVO
    
    @property
    def is_abono_recibido(self) -> bool:
        return self.invoice_type == InvoiceType.ABONO_RECIBIDO
    
    @property
    def is_saldo_inicial(self) -> bool:
        return self.invoice_type == InvoiceType.SALDO_INICIAL


class PeriodFilter(BaseModel):
    """Date range filter"""
    fecha_inicio: date
    fecha_fin: date
    modo: str = "Rango"  # Rango, Día, Semana, Mes, Todo
    
    def contains(self, dt: datetime) -> bool:
        d = dt.date() if isinstance(dt, datetime) else dt
        return self.fecha_inicio <= d <= self.fecha_fin


class SalesBreakdown(BaseModel):
    """Breakdown of sales by source/method"""
    sirvoy_bruto: Decimal = Decimal("0")
    sirvoy_tarjeta: Decimal = Decimal("0")
    sirvoy_transferencia: Decimal = Decimal("0")
    sirvoy_efectivo: Decimal = Decimal("0")
    plataformas_online: Decimal = Decimal("0")  # Izipay/Culqi/Openpay web
    plataformas_pos: Decimal = Decimal("0")     # POS manual
    total_confirmado: Decimal = Decimal("0")    # Online + Transferencia + Efectivo + POS


class CostBreakdown(BaseModel):
    """Breakdown of operational costs"""
    fb_ads: Decimal = Decimal("0")
    sirvoy_software: Decimal = Decimal("0")
    asistente: Decimal = Decimal("0")
    extra: Decimal = Decimal("0")
    total: Decimal = Decimal("0")


class DashboardKPIs(BaseModel):
    """All KPIs for the dashboard header"""
    ventas_sirvoy: Decimal = Decimal("0")
    recibido_confirmado: Decimal = Decimal("0")
    costos_operativos: Decimal = Decimal("0")
    saldo_pendiente: Decimal = Decimal("0")
    comision_acumulada: Decimal = Decimal("0")
    pendiente_confirmacion: Decimal = Decimal("0")
    transacciones_count: int = 0
    
    @property
    def comision_periodo(self) -> Decimal:
        from core.calculations import COMMISSION_RATE
        return (self.ventas_sirvoy * COMMISSION_RATE).quantize(Decimal("0.01"))


class ReconciliationResult(BaseModel):
    """Result of invoice vs abono reconciliation"""
    total_facturado_comision: Decimal = Decimal("0")
    total_facturado_costos: Decimal = Decimal("0")
    total_abonos_registrados: Decimal = Decimal("0")
    diferencia: Decimal = Decimal("0")
    facturas_vencidas: List[Invoice] = Field(default_factory=list)
    facturas_pagadas_sin_abono: List[Invoice] = Field(default_factory=list)


def quantize(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places"""
    return value.quantize(Decimal("0.01"))