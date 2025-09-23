# Technology Stack

## Data Processing Environment

This is a **data analysis and reporting project** focused on payment transaction processing. The primary technology stack consists of:

### Core Technologies
- **Data Format**: CSV files for transaction data import/export
- **Spreadsheet Analysis**: Excel (.xlsx) for sales reporting and analysis
- **Platform**: Windows-based data processing environment

### Payment Gateway APIs
- **Izipay**: Transaction export via CSV format
- **Culqi**: Transaction export via CSV format with POS terminal integration
- **Banking**: Direct transfer data processing

### Data Structure
- **Primary Currency**: PEN (Peruvian Sol)
- **Date Format**: DD/MM/YYYY HH:MM:SS (24-hour format)
- **Decimal Separator**: Period (.) for amounts
- **Field Separator**: Semicolon (;) for Izipay data, comma (,) for Culqi data

## Common Operations

### Data Import/Export
```bash
# View CSV structure
type filename.csv | more

# Basic file operations
dir *.csv
copy source.csv backup.csv
```

### Data Validation
- Verify transaction amounts match between processors
- Check date ranges for reporting periods
- Validate customer email formats and payment status
- Cross-reference transaction IDs across systems

### Reporting Periods
- Weekly sales summaries (Monday to Sunday)
- Monthly reconciliation reports
- Commission calculations per payment processor