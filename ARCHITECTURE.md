# Refactor Architecture — Peña Linda Bungalows Commission Dashboard

## Current Problems
- 1700+ line monolith mixing data, calculations, UI
- Two collections with overlapping/confusing semantics (`pagos`, `cobros`)
- Business logic hardcoded in Streamlit callbacks
- No role distinction (Admin vs Hotelier)
- Missing "Monto Pendiente de Confirmar" for POS manual transactions
- No testability

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT APP                            │
├─────────────────────────────────────────────────────────────────┤
│  pages/                                                         │
│  ├── 0_🏠_Dashboard.py          # Role-aware landing            │
│  ├── 1_📊_Ventas.py             # Sales view (both roles)       │
│  ├── 2_💸_Costos.py             # Costs view (admin only)       │
│  ├── 3_🔄_Conciliacion.py       # Reconciliation (admin)        │
│  ├── 4_📋_Historial.py          # History & QB reconciliation   │
│  ├── 5_🏨_Hotelier_View.py      # Simplified hotelier view      │
│  └── 6_⚙️_Admin_Tools.py        # POS upload, settings (admin)  │
├─────────────────────────────────────────────────────────────────┤
│  components/                                                    │
│  ├── kpi_cards.py               # Reusable KPI components       │
│  ├── charts.py                  # Chart components              │
│  ├── tables.py                  # Editable table components     │
│  ├── forms.py                   # Form components               │
│  └── sidebar.py                 # Shared sidebar                │
├─────────────────────────────────────────────────────────────────┤
│  core/                                                          │
│  ├── config.py                  # Settings, constants           │
│  ├── models.py                  # Pydantic models               │
│  ├── database.py                # MongoDB connection, repos     │
│  ├── calculations.py            # Pure calculation functions    │
│  ├── auth.py                    # Role detection                │
│  └── utils.py                   # Helpers                       │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model (Clean)

### `pagos` → **Transactions** (Source of truth for money movement)
| Field | Type | Description |
|-------|------|-------------|
| `source` | Enum | `sirvoy`, `izipay_online`, `culqi`, `openpay`, `izipay_pos`, `culqi_pos`, `openpay_pos`, `abono_chamba`, `costo_fb`, `costo_sirvoy`, `costo_asistente`, `costo_extra`, `saldo_base` |
| `tx_type` | Enum | `venta`, `costo`, `abono`, `saldo_inicial` |
| `amount` | Decimal | Positive for ingresos, negative for egresos |
| `currency` | String | `PEN` |
| `method` | String | `VISA`, `Transferencia`, `Efectivo`, `Yape`, `POS`, etc. |
| `reference` | String | External reference / transaction ID |
| `fecha` | DateTime | Peru timezone (UTC-5) |
| `commission` | Decimal | Calculated commission if venta |
| `metadata` | Dict | Flexible extra data |
| `hash` | String | Deduplication key |

### `cobros` → **Invoices** (Chamba → Peña Linda billing)
| Field | Type | Description |
|-------|------|-------------|
| `invoice_type` | Enum | `comision`, `costo_operativo`, `abono_recibido`, `saldo_inicial` |
| `category` | String | `Facebook Ads`, `Sirvoy`, `Asistente`, `Extra`, etc. |
| `amount` | Decimal | Always positive |
| `currency` | String | `PEN` |
| `fecha_emision` | DateTime | When invoice was issued |
| `fecha_vencimiento` | DateTime | Due date |
| `estado_qb` | Enum | `pagada`, `vencida`, `pendiente`, `parcial` |
| `qb_ref` | String | QuickBooks invoice number |
| `periodo_inicio` | Date | Period covered start |
| `periodo_fin` | Date | Period covered end |
| `hash` | String | Deduplication key |

## Business Rules (Pure Functions)

```python
# calculations.py

COMMISSION_RATE = Decimal("0.05")
BASE_DATE = date(2026, 3, 3)
SALDO_BASE = Decimal("9654.83")

def calculate_period_commission(sirvoy_sales: Decimal) -> Decimal:
    """5% commission on Sirvoy gross sales for a period."""
    return (sirvoy_sales * COMMISSION_RATE).quantize(Decimal("0.01"))

def calculate_deuda(
    comision_periodo: Decimal,
    costos_periodo: Decimal,
    abonos_periodo: Decimal,
    include_historical: bool = True
) -> Decimal:
    """
    Deuda = Comisión + Costos - Abonos (+ Saldo Base if historical)
    """
    base = SALDO_BASE if include_historical else Decimal("0")
    return max(Decimal("0"), base + comision_periodo + costos_periodo - abonos_periodo)

def calculate_pendiente_confirmacion(
    sirvoy_tarjeta: Decimal,
    plataformas_online: Decimal,
    pos_manual: Decimal
) -> Decimal:
    """
    Monto pendiente de confirmar = Tarjeta Sirvoy - (Plataformas Online + POS Manual)
    
    Sirvoy registra todas las ventas con tarjeta.
    Plataformas online (Izipay/Culqi/Openpay web) confirman algunas.
    POS manual (Izipay POS, Culqi POS, Openpay POS) confirma el resto.
    Lo que queda = pendiente de confirmar / posible embargo.
    """
    confirmado_online = plataformas_online + pos_manual
    return max(Decimal("0"), sirvoy_tarjeta - confirmado_online)

def split_by_role(user_role: str) -> dict:
    """
    Admin: sees everything (costos, comisiones, abonos, POS manual upload)
    Hotelier: sees ventas, comisiones, estado de deuda, NO costos operativos internos
    """
    permissions = {
        "admin": {"ventas": True, "costos": True, "abonos": True, "pos_manual": True, "historial": True, "config": True},
        "hotelier": {"ventas": True, "costos": False, "abonos": True, "pos_manual": True, "historial": True, "config": False},
    }
    return permissions.get(user_role, permissions["hotelier"])
```

## Role-Based Views

### Admin (Chamba Digital / Yosward)
- Full dashboard: Ventas, Costos, Conciliación, Historial, POS Manual Upload, Config
- Can upload POS reports (Izipay POS, Culqi POS, Openpay POS)
- Manages cost categories, commission rate, base date

### Hotelier (Peña Linda / Juan Mariano)
- Simplified: "Mi Hotel" view
- Ventas del período, Comisión generada, Deuda actual
- Puede cargar POS manual (ellos tienen los terminales físicos)
- Ve "Monto Pendiente de Confirmar" claro
- NO ve desglose de costos internos (FB Ads, Sirvoy, Asistente)

## UI Design Principles (per frontend-design skill)

### Palette - Ocean/Coastal Identity (Peña Linda = beach bungalows)
| Role | Name | Hex | Usage |
|------|------|-----|-------|
| Primary | **Deep Pacific** | `#0c2d48` | Headers, primary actions |
| Secondary | **Turquoise** | `#0d9488` | Accent, success states |
| Tertiary | **Sand** | `#f5f0e1` | Light backgrounds |
| Alert | **Coral** | `#f97316` | Warnings, pending amounts |
| Danger | **Deep Red** | `#b91c1c` | Errors, overdue |
| Neutral | **Foam** | `#e0f2f1` | Cards, subtle borders |
| Text Dark | **Tide** | `#111827` | Primary text |
| Text Muted | **Mist** | `#6b7280` | Secondary text |

### Typography
- **Display**: `Inter` (already used) - clean, legible at small sizes
- **Data/Mono**: `JetBrains Mono` or `SF Mono` - for amounts, references
- **Scale**: `clamp(0.875rem, 0.8rem + 0.5vw, 1rem)` base

### Signature Element
**The "Wave" Progress Bar** - A single animated gradient bar showing:
```
Deuda Actual ─────────────────────────────────► Pagado
     S/ 45,230                                    S/ 12,100
```
This IS the dashboard - everything else supports this one number.

## Feature: Monto Pendiente de Confirmar

### Data Flow
```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Sirvoy Web     │     │  Izipay/Culqi/   │     │   POS Manual     │
│  (Todas tarjetas)│────►│  Online (Web)    │     │  (Terminales     │
└──────────────────┘     └──────────────────┘     │   físicos)       │
       │                       │                  └────────┬─────────┘
       │                       │                           │
       ▼                       ▼                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              calculate_pendiente_confirmacion()                  │
│  Sirvoy_Tarjeta - (Plataformas_Online + POS_Manual) = Pendiente  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   KPI Card:       │
                    │  ⏳ Pendiente     │
                    │  Confirmar        │
                    │  S/ XX,XXX.XX     │
                    └───────────────────┘
```

### POS Manual Upload (Admin/Hotelier)
- CSV/Excel upload per provider
- Auto-detect format (Izipay POS, Culqi POS, Openpay POS)
- Preview + confirm before insert
- Stores in `transactions` with `source: izipay_pos`, `culqi_pos`, `openpay_pos`

## Migration Strategy

1. **Phase 1**: Create `core/` modules, migrate calculations to pure functions
2. **Phase 2**: Build `components/` library
3. **Phase 3**: Create Streamlit multipage app with role routing
4. **Phase 4**: Migrate data - add `source` enum, backfill POS types
5. **Phase 5**: Deprecate old `panel_control.py`

## File Structure After Refactor

```
calculadora-comisiones-pena-linda/
├── .streamlit/
│   └── config.toml
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── database.py
│   ├── calculations.py
│   ├── auth.py
│   └── utils.py
├── components/
│   ├── __init__.py
│   ├── kpi_cards.py
│   ├── charts.py
│   ├── tables.py
│   ├── forms.py
│   └── sidebar.py
├── pages/
│   ├── 0_🏠_Dashboard.py
│   ├── 1_📊_Ventas.py
│   ├── 2_💸_Costos.py
│   ├── 3_🔄_Conciliacion.py
│   ├── 4_📋_Historial.py
│   ├── 5_🏨_Hotelier_View.py
│   └── 6_⚙️_Admin_Tools.py
├── data/
│   └── seed_db.json
├── scripts/
│   ├── migrate_data.py
│   ├── import_qb.py
│   └── import_pos.py
├── tests/
│   ├── test_calculations.py
│   └── test_models.py
├── panel_control.py          # LEGACY - keep for rollback
├── requirements.txt
└── README.md
```