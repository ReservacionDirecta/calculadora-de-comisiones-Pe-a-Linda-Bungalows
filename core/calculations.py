# core/calculations.py
"""Pure calculation functions - no side effects, fully testable"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional
from .models import (
    Transaction,
    TransactionSource,
    TransactionType,
    Invoice,
    InvoiceType,
    InvoiceStatus,
    PeriodFilter,
    SalesBreakdown,
    CostBreakdown,
    DashboardKPIs,
    ReconciliationResult,
    Role,
    Permissions,
)


# Constants
COMMISSION_RATE = Decimal("0.05")
BASE_DATE = date(2026, 3, 3)
SALDO_BASE = Decimal("9654.83")


def quantize(value: Decimal) -> Decimal:
    """Round to 2 decimal places"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def filter_by_period(transactions: List[Transaction], period: PeriodFilter) -> List[Transaction]:
    """Filter transactions by period"""
    return [t for t in transactions if period.contains(t.fecha)]


def filter_since_base(transactions: List[Transaction]) -> List[Transaction]:
    """Filter transactions since BASE_DATE (03/03/2026)"""
    return [t for t in transactions if t.fecha.date() >= BASE_DATE]


def calculate_sales_breakdown(
    transactions: List[Transaction],
    period: PeriodFilter
) -> SalesBreakdown:
    """Calculate complete sales breakdown for a period"""
    period_tx = filter_by_period(transactions, period)
    sales = [t for t in period_tx if t.is_sale]
    
    sirvoy = [t for t in sales if t.source == TransactionSource.SIRVOY]
    plataformas_online = [t for t in sales if t.source.is_platform_online]
    plataformas_pos = [t for t in sales if t.source.is_platform_pos]
    
    sirvoy_bruto = sum((t.amount for t in sirvoy), Decimal("0"))
    sirvoy_tarjeta = sum(
        (t.amount for t in sirvoy if t.metadata.get("tipo_pago") == "Tarjeta"),
        Decimal("0")
    )
    sirvoy_transferencia = sum(
        (t.amount for t in sirvoy if t.metadata.get("tipo_pago") == "Transferencia"),
        Decimal("0")
    )
    sirvoy_efectivo = sum(
        (t.amount for t in sirvoy if t.metadata.get("tipo_pago") == "Efectivo"),
        Decimal("0")
    )
    
    plataformas_online_total = sum((t.amount for t in plataformas_online), Decimal("0"))
    plataformas_pos_total = sum((t.amount for t in plataformas_pos), Decimal("0"))
    
    total_confirmado = (
        plataformas_online_total + 
        sirvoy_transferencia + 
        sirvoy_efectivo + 
        plataformas_pos_total
    )
    
    return SalesBreakdown(
        sirvoy_bruto=quantize(sirvoy_bruto),
        sirvoy_tarjeta=quantize(sirvoy_tarjeta),
        sirvoy_transferencia=quantize(sirvoy_transferencia),
        sirvoy_efectivo=quantize(sirvoy_efectivo),
        plataformas_online=quantize(plataformas_online_total),
        plataformas_pos=quantize(plataformas_pos_total),
        total_confirmado=quantize(total_confirmado),
    )


def calculate_cost_breakdown(
    transactions: List[Transaction],
    period: PeriodFilter
) -> CostBreakdown:
    """Calculate cost breakdown for a period"""
    period_tx = filter_by_period(transactions, period)
    costs = [t for t in period_tx if t.is_cost]
    
    fb = sum((t.amount for t in costs if t.source == TransactionSource.COSTO_FB), Decimal("0"))
    sirvoy = sum((t.amount for t in costs if t.source == TransactionSource.COSTO_SIRVOY), Decimal("0"))
    asistente = sum((t.amount for t in costs if t.source == TransactionSource.COSTO_ASISTENTE), Decimal("0"))
    extra = sum((t.amount for t in costs if t.source == TransactionSource.COSTO_EXTRA), Decimal("0"))
    
    total = fb + sirvoy + asistente + extra
    
    return CostBreakdown(
        fb_ads=quantize(fb),
        sirvoy_software=quantize(sirvoy),
        asistente=quantize(asistente),
        extra=quantize(extra),
        total=quantize(total),
    )


def calculate_abonos(transactions: List[Transaction], period: PeriodFilter) -> Decimal:
    """Calculate total abonos in period"""
    period_tx = filter_by_period(transactions, period)
    abonos = [t for t in period_tx if t.is_abono]
    return quantize(sum((t.amount for t in abonos), Decimal("0")))


def calculate_period_commission(sirvoy_bruto: Decimal) -> Decimal:
    """Calculate 5% commission on Sirvoy gross"""
    return quantize(sirvoy_bruto * COMMISSION_RATE)


def calculate_deuda(
    sales: SalesBreakdown,
    costs: CostBreakdown,
    abonos: Decimal,
    include_saldo_base: bool = True
) -> Decimal:
    """Calculate debt for a period"""
    comision = calculate_period_commission(sales.sirvoy_bruto)
    deuda = comision + costs.total - abonos
    if include_saldo_base:
        deuda += SALDO_BASE
    return max(quantize(deuda), Decimal("0"))


def calculate_pendiente_confirmacion(
    sirvoy_tarjeta: Decimal,
    plataformas_online: Decimal
) -> Decimal:
    """Calculate amount pending confirmation from POS platforms"""
    pendiente = sirvoy_tarjeta - plataformas_online
    return max(quantize(pendiente), Decimal("0"))


def calculate_historical_since_base(transactions: List[Transaction]) -> Dict[str, Decimal]:
    """Calculate all accumulated values since BASE_DATE"""
    since_base = filter_since_base(transactions)
    
    # Sales - only Sirvoy for commission
    sirvoy_sales = [t for t in since_base if t.source == TransactionSource.SIRVOY and t.is_sale]
    comision_acum = sum((t.amount for t in sirvoy_sales), Decimal("0")) * COMMISSION_RATE
    
    # Costs
    costs = [t for t in since_base if t.is_cost]
    costos_acum = sum((t.amount for t in costs), Decimal("0"))
    
    # Abonos
    abonos = [t for t in since_base if t.is_abono]
    abonos_acum = sum((t.amount for t in abonos), Decimal("0"))
    
    return {
        "comision_acumulada": quantize(comision_acum),
        "costos_acumulados": quantize(costos_acum),
        "abonos_acumulados": quantize(abonos_acum),
        "deuda_historica": quantize(comision_acum + costos_acum + SALDO_BASE - abonos_acum),
    }


def calculate_kpis(
    transactions: List[Transaction],
    period: PeriodFilter,
    historical: Dict[str, Decimal]
) -> DashboardKPIs:
    """Calculate all dashboard KPIs"""
    sales = calculate_sales_breakdown(transactions, period)
    costs = calculate_cost_breakdown(transactions, period)
    abonos = calculate_abonos(transactions, period)
    deuda = calculate_deuda(sales, costs, abonos)
    pendiente = calculate_pendiente_confirmacion(
        sales.sirvoy_tarjeta,
        sales.plataformas_online
    )
    
    sirvoy_count = len([
        t for t in filter_by_period(transactions, period)
        if t.source == TransactionSource.SIRVOY and t.is_sale
    ])
    
    return DashboardKPIs(
        ventas_sirvoy=sales.sirvoy_bruto,
        recibido_confirmado=sales.total_confirmado,
        costos_operativos=costs.total,
        saldo_pendiente=deuda,
        comision_acumulada=historical["comision_acumulada"],
        pendiente_confirmacion=pendiente,
        transacciones_count=sirvoy_count,
    )


def get_role_permissions(role: Role) -> Permissions:
    """Get permissions for a role"""
    if role == Role.ADMIN:
        return Permissions(
            ventas=True,
            costos=True,
            abonos=True,
            pos_manual=True,
            historial=True,
            config=True,
        )
    return Permissions(
        ventas=True,
        costos=False,
        abonos=True,
        pos_manual=True,
        historial=True,
        config=False,
    )


def reconcile_invoices_vs_abonos(
    invoices: List[Invoice],
    abonos: List[Transaction]
) -> ReconciliationResult:
    """Reconcile QuickBooks invoices vs recorded abonos"""
    facturas_comision = [i for i in invoices if i.is_comision]
    facturas_costo = [i for i in invoices if i.is_costo]
    
    total_fact_comision = sum((i.amount for i in facturas_comision), Decimal("0"))
    total_fact_costo = sum((i.amount for i in facturas_costo), Decimal("0"))
    total_abonos = sum((a.amount for a in abonos), Decimal("0"))
    
    # Facturas vencidas (no pagadas en QB)
    vencidas = [i for i in invoices if i.estado_qb == InvoiceStatus.VENCIDA]
    
    # Facturas pagadas en QB pero sin abono correspondiente
    pagadas_sin_abono = []
    for inv in invoices:
        if inv.estado_qb == InvoiceStatus.PAGADA:
            has_match = any(
                abs(a.amount - inv.amount) < Decimal("1") and
                abs((a.fecha.date() - inv.fecha_emision.date()).days) < 7
                for a in abonos
            )
            if not has_match:
                pagadas_sin_abono.append(inv)
    
    return ReconciliationResult(
        total_facturado_comision=quantize(total_fact_comision),
        total_facturado_costos=quantize(total_fact_costo),
        total_abonos_registrados=quantize(total_abonos),
        diferencia=quantize(total_fact_comision - total_abonos),
        facturas_vencidas=vencidas,
        facturas_pagadas_sin_abono=pagadas_sin_abono,
    )