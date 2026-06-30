# core/database.py
"""MongoDB connection and repository layer"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Iterator
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId
from .config import settings
from .models import Transaction, TransactionSource, TransactionType, Invoice, InvoiceType


class DatabaseManager:
    """Singleton MongoDB connection manager"""
    _instance: Optional[DatabaseManager] = None
    _client: Optional[MongoClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._client = MongoClient(
                settings.mongo_url,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
            )
    
    @property
    def db(self) -> Database:
        return self._client[settings.db_name]
    
    @property
    def transactions(self) -> Collection:
        return self.db["pagos"]  # Legacy collection name
    
    @property
    def invoices(self) -> Collection:
        return self.db["cobros"]  # Legacy collection name
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None


# Global instance
db_manager = DatabaseManager()


def get_db() -> Database:
    return db_manager.db


def get_transactions_collection() -> Collection:
    return db_manager.transactions


def get_invoices_collection() -> Collection:
    return db_manager.invoices


# --- Repository Functions ---

def fetch_all_transactions() -> List[Transaction]:
    """Fetch all transactions from MongoDB and normalize to Transaction model"""
    coll = get_transactions_collection()
    docs = list(coll.find({}, {"hash": 0}))  # Exclude hash for performance
    return [_doc_to_transaction(doc) for doc in docs]


def fetch_transactions_by_period(
    fecha_inicio: datetime,
    fecha_fin: datetime
) -> List[Transaction]:
    """Fetch transactions within a date range"""
    coll = get_transactions_collection()
    docs = list(coll.find({
        "fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}
    }, {"hash": 0}))
    return [_doc_to_transaction(doc) for doc in docs]


def fetch_transactions_since_base() -> List[Transaction]:
    """Fetch transactions since BASE_DATE (03/03/2026)"""
    from .calculations import BASE_DATE
    coll = get_transactions_collection()
    docs = list(coll.find({
        "fecha": {"$gte": BASE_DATE}
    }, {"hash": 0}))
    return [_doc_to_transaction(doc) for doc in docs]


def fetch_all_invoices() -> List[Invoice]:
    """Fetch all invoices from MongoDB and normalize to Invoice model"""
    coll = get_invoices_collection()
    docs = list(coll.find({}))
    return [_doc_to_invoice(doc) for doc in docs]


def fetch_invoices_by_type(invoice_type: InvoiceType) -> List[Invoice]:
    """Fetch invoices by type"""
    coll = get_invoices_collection()
    docs = list(coll.find({"tipo": invoice_type.value}))
    return [_doc_to_invoice(doc) for doc in docs]


def fetch_abonos() -> List[Transaction]:
    """Fetch all abonos (tipo_pago: Abono)"""
    coll = get_transactions_collection()
    docs = list(coll.find({"tipo_pago": "Abono"}))
    return [_doc_to_transaction(doc) for doc in docs]


def insert_transaction(tx: Transaction) -> str:
    """Insert a transaction, return inserted ID"""
    coll = get_transactions_collection()
    doc = _transaction_to_doc(tx)
    result = coll.insert_one(doc)
    return str(result.inserted_id)


def insert_invoice(inv: Invoice) -> str:
    """Insert an invoice, return inserted ID"""
    coll = get_invoices_collection()
    doc = _invoice_to_doc(inv)
    result = coll.insert_one(doc)
    return str(result.inserted_id)


def upsert_transactions(transactions: List[Transaction]) -> tuple:
    """Bulk upsert transactions by hash (deduplication)"""
    coll = get_transactions_collection()
    operations = []
    for tx in transactions:
        doc = _transaction_to_doc(tx)
        operations.append(
            {"updateOne": {"filter": {"hash": tx.hash}, "update": {"$set": doc}, "upsert": True}}
        )
    if operations:
        result = coll.bulk_write(operations, ordered=False)
        return result.upserted_count, result.modified_count
    return 0, 0


def delete_transaction(transaction_id: str) -> bool:
    """Delete a transaction by ID"""
    coll = get_transactions_collection()
    result = coll.delete_one({"_id": ObjectId(transaction_id)})
    return result.deleted_count > 0


def clear_all_transactions() -> int:
    """Clear all transactions (use with caution!)"""
    coll = get_transactions_collection()
    result = coll.delete_many({})
    return result.deleted_count


# --- Document <-> Model Conversion ---

def _doc_to_transaction(doc: dict) -> Transaction:
    """Convert MongoDB document to Transaction model"""
    # Map legacy source to TransactionSource
    source_map = {
        "Sirvoy": TransactionSource.SIRVOY,
        "Izipay": TransactionSource.IZIPAY_ONLINE,
        "Culqi": TransactionSource.CULQI_ONLINE,
        "Openpay": TransactionSource.OPENPAY_ONLINE,
        "Costo FB Ads": TransactionSource.COSTO_FB,
        "Costo Sirvoy": TransactionSource.COSTO_SIRVOY,
        "Costo Asistente": TransactionSource.COSTO_ASISTENTE,
        "Costo Extra": TransactionSource.COSTO_EXTRA,
        "Abono Chamba": TransactionSource.ABONO_CHAMBA,
        "Saldo Base": TransactionSource.SALDO_BASE,
    }
    
    # Map tipo_pago to TransactionType
    tipo_map = {
        "Tarjeta": TransactionType.VENTA,
        "Transferencia": TransactionType.VENTA,
        "Efectivo": TransactionType.VENTA,
        "Otros": TransactionType.VENTA,
        "Costo": TransactionType.COSTO,
        "Abono": TransactionType.ABONO,
    }
    
    fuente = doc.get("fuente", "")
    tipo_pago = doc.get("tipo_pago", "")
    
    source = source_map.get(fuente, TransactionSource.SIRVOY)
    tx_type = tipo_map.get(tipo_pago, TransactionType.VENTA)
    
    # Handle fecha
    fecha = doc.get("fecha")
    if isinstance(fecha, str):
        fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    
    # Handle amount
    monto = doc.get("monto", 0)
    if isinstance(monto, str):
        monto = Decimal(monto.replace(",", ""))
    else:
        monto = Decimal(str(monto))
    
    # Build metadata
    metadata = {
        "tipo_pago": tipo_pago,
        "comprador": doc.get("comprador", ""),
        "es_link": doc.get("es_link", False),
        "estado_deposito": doc.get("estado_deposito", ""),
    }
    
    return Transaction(
        id=str(doc.get("_id", "")),
        source=source,
        tx_type=tx_type,
        amount=monto,
        currency=doc.get("moneda", "PEN"),
        method=doc.get("metodo", ""),
        reference=doc.get("referencia", doc.get("transaction_id", "")),
        fecha=fecha,
        fecha_pe=fecha,  # Will be converted to Peru TZ in service layer
        commission=Decimal(str(doc.get("comision", 0))),
        metadata=metadata,
        hash=doc.get("hash", ""),
        created_at=doc.get("_cargado", datetime.now()),
    )


def _transaction_to_doc(tx: Transaction) -> dict:
    """Convert Transaction model to MongoDB document"""
    # Reverse map source
    source_reverse = {
        TransactionSource.SIRVOY: "Sirvoy",
        TransactionSource.IZIPAY_ONLINE: "Izipay",
        TransactionSource.CULQI_ONLINE: "Culqi",
        TransactionSource.OPENPAY_ONLINE: "Openpay",
        TransactionSource.IZIPAY_POS: "Izipay POS",
        TransactionSource.CULQI_POS: "Culqi POS",
        TransactionSource.OPENPAY_POS: "Openpay POS",
        TransactionSource.COSTO_FB: "Costo FB Ads",
        TransactionSource.COSTO_SIRVOY: "Costo Sirvoy",
        TransactionSource.COSTO_ASISTENTE: "Costo Asistente",
        TransactionSource.COSTO_EXTRA: "Costo Extra",
        TransactionSource.ABONO_CHAMBA: "Abono Chamba",
        TransactionSource.SALDO_BASE: "Saldo Base",
    }
    
    tipo_reverse = {
        TransactionType.VENTA: tx.metadata.get("tipo_pago", "Tarjeta"),
        TransactionType.COSTO: "Costo",
        TransactionType.ABONO: "Abono",
        TransactionType.SALDO_INICIAL: "Costo",
    }
    
    return {
        "fuente": source_reverse.get(tx.source, "Sirvoy"),
        "tipo_pago": tipo_reverse.get(tx.tx_type, "Tarjeta"),
        "monto": float(tx.amount),
        "moneda": tx.currency,
        "metodo": tx.method,
        "referencia": tx.reference,
        "fecha": tx.fecha,
        "comision": float(tx.commission),
        "comprador": tx.metadata.get("comprador", ""),
        "es_link": tx.metadata.get("es_link", False),
        "estado_deposito": tx.metadata.get("estado_deposito", ""),
        "hash": tx.hash,
        "_cargado": tx.created_at,
    }


def _doc_to_invoice(doc: dict) -> Invoice:
    """Convert MongoDB document to Invoice model"""
    tipo_map = {
        "comision": InvoiceType.COMISION,
        "costo": InvoiceType.COSTO_OPERATIVO,
        "abono": InvoiceType.ABONO_RECIBIDO,
        "saldo_inicial": InvoiceType.SALDO_INICIAL,
    }
    
    estado_map = {
        "Pagada": InvoiceStatus.PAGADA,
        "Vencido": InvoiceStatus.VENCIDA,
        "Vencida": InvoiceStatus.VENCIDA,
        "Pendiente": InvoiceStatus.PENDIENTE,
    }
    
    fecha = doc.get("fecha")
    if isinstance(fecha, str):
        fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    
    monto = doc.get("monto", 0)
    if isinstance(monto, str):
        monto = Decimal(monto.replace(",", ""))
    else:
        monto = Decimal(str(monto))
    
    return Invoice(
        id=str(doc.get("_id", "")),
        invoice_type=tipo_map.get(doc.get("tipo", "costo"), InvoiceType.COSTO_OPERATIVO),
        category=doc.get("categoria", doc.get("concepto", "")),
        amount=monto,
        currency=doc.get("moneda", "PEN"),
        fecha_emision=fecha,
        fecha_vencimiento=doc.get("fecha_vencimiento"),
        estado_qb=estado_map.get(doc.get("qbo_estado", "Pendiente"), InvoiceStatus.PENDIENTE),
        qb_ref=doc.get("qbo_ref", ""),
        periodo_inicio=doc.get("periodo_inicio"),
        periodo_fin=doc.get("periodo_fin"),
        hash=doc.get("hash", ""),
        origen_importacion=doc.get("origen_importacion", ""),
        created_at=doc.get("_cargado", datetime.now()),
    )


def _invoice_to_doc(inv: Invoice) -> dict:
    """Convert Invoice model to MongoDB document"""
    tipo_reverse = {
        InvoiceType.COMISION: "comision",
        InvoiceType.COSTO_OPERATIVO: "costo",
        InvoiceType.ABONO_RECIBIDO: "abono",
        InvoiceType.SALDO_INICIAL: "saldo_inicial",
    }
    
    estado_reverse = {
        InvoiceStatus.PAGADA: "Pagada",
        InvoiceStatus.VENCIDA: "Vencido",
        InvoiceStatus.PENDIENTE: "Pendiente",
        InvoiceStatus.PARCIAL: "Parcial",
    }
    
    return {
        "tipo": tipo_reverse.get(inv.invoice_type, "costo"),
        "categoria": inv.category,
        "concepto": inv.category,
        "monto": float(inv.amount),
        "moneda": inv.currency,
        "fecha": inv.fecha_emision,
        "fecha_vencimiento": inv.fecha_vencimiento,
        "qbo_estado": estado_reverse.get(inv.estado_qb, "Pendiente"),
        "qbo_ref": inv.qb_ref,
        "periodo_inicio": inv.periodo_inicio,
        "periodo_fin": inv.periodo_fin,
        "hash": inv.hash,
        "origen_importacion": inv.origen_importacion,
        "_cargado": inv.created_at,
    }