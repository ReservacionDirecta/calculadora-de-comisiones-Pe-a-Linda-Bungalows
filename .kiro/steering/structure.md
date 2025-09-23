# Project Structure

## File Organization

This project follows a simple data-centric structure focused on payment processing and sales analysis:

### Root Directory Structure
```
/
├── .kiro/                          # Kiro configuration and steering
│   └── steering/                   # AI assistant guidance documents
├── *.csv                          # Transaction data files
└── *.xlsx                         # Sales reports and analysis
```

## File Naming Conventions

### Transaction Data Files
- **Izipay exports**: `Listado_transacciones_capturadas-izipay.csv`
- **Culqi exports**: `ventas_YYYYMMDD_culqi.csv`
- **Secured/processed data**: `secured.csv`
- **Date format in filenames**: YYYYMMDD

### Sales Reports
- **Excel reports**: `Resumen de Ventas [Business Name] del DD al DD de [month] YYYY.xlsx`
- **Backup copies**: Prefix with "Copia de" for backup versions

## Data File Standards

### CSV Structure
- **Izipay**: Semicolon-separated (;) with Spanish headers
- **Culqi**: Comma-separated (,) with Spanish headers
- **Encoding**: UTF-8 with BOM for Spanish characters
- **Headers**: Always include column headers in first row

### Key Data Fields
- **Transaction ID**: Unique identifier per processor
- **Amount**: Decimal format with period separator
- **Date/Time**: DD/MM/YYYY HH:MM:SS format
- **Payment Method**: Visa, Mastercard, Amex, Yape, etc.
- **Status**: Captured, Authorized, Declined, etc.
- **Customer Info**: Name, email, document number

## Processing Workflow
1. **Import** raw transaction data from payment processors
2. **Validate** data integrity and format consistency  
3. **Process** commission calculations and reconciliation
4. **Export** consolidated reports for business analysis
5. **Archive** processed data with appropriate naming