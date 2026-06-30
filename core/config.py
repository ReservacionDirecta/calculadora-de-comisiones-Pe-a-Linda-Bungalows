# core/config.py
"""Configuration settings"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Application settings - immutable configuration"""
    # Database
    mongo_url: str = os.environ.get("MONGO_URL", "mongodb://localhost:27017/pena_linda")
    
    # Business constants
    commission_rate: float = 0.05  # 5%
    base_date: str = "2026-03-03"
    saldo_base: float = 9654.83
    
    # Timezone
    peru_tz: str = "America/Lima"
    
    # UI
    page_title: str = "Peña Linda Bungalows — Comisión"
    page_icon: str = "🏝️"
    
    # Cache
    cache_ttl_seconds: int = 300
    
    # Pagination
    default_page_size: int = 25
    page_size_options: tuple = (25, 50, 100)
    
    # Sources that count as "sales" (not costs/abonos)
    sales_sources: tuple = ("Sirvoy", "Izipay", "Culqi", "Openpay", "Otros")
    cost_sources: tuple = ("Costo FB Ads", "Costo Sirvoy", "Costo Asistente", "Costo Extra")
    abono_source: str = "Abono Chamba"
    saldo_base_source: str = "Saldo Base"
    
    # POS platforms for "pendiente de confirmar"
    pos_platforms: tuple = ("Izipay", "Culqi", "Openpay")
    
    @property
    def all_sources(self) -> tuple:
        return self.sales_sources + self.cost_sources + (self.abono_source, self.saldo_base_source)


settings = Settings()