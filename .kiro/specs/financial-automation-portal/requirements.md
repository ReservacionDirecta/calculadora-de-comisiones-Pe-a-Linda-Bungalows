# Requirements Document

## Introduction

The Financial Automation Portal is a web-based tool designed to help users manage and analyze their financial income and expenses. The system consolidates data from multiple sources (payment gateways and booking systems) to provide clear financial insights and calculate net profit. The portal supports CSV file uploads, automatic data source detection, manual data entry, filtering capabilities, and comprehensive financial reporting.

## Requirements

### Requirement 1

**User Story:** As a business owner, I want to upload multiple CSV files simultaneously, so that I can process income data from different platforms efficiently.

#### Acceptance Criteria

1. WHEN a user clicks "Upload CSV Files" THEN the system SHALL display a file selection dialog that allows multiple file selection
2. WHEN multiple CSV files are selected THEN the system SHALL process all files simultaneously
3. WHEN files are being processed THEN the system SHALL display a loading indicator
4. IF a file upload fails THEN the system SHALL display an error message and continue processing remaining files
5. WHEN file processing is complete THEN the system SHALL display a success message with the number of records processed

### Requirement 2

**User Story:** As a user, I want the system to automatically detect data formats from Izipay, Culqi, and Sirvoy, so that I don't need to manually specify the data source.

#### Acceptance Criteria

1. WHEN a CSV file is uploaded THEN the system SHALL automatically analyze the file structure and headers
2. IF the file matches Izipay format THEN the system SHALL parse it using Izipay-specific rules
3. IF the file matches Culqi format THEN the system SHALL parse it using Culqi-specific rules
4. IF the file matches Sirvoy format THEN the system SHALL parse it using Sirvoy-specific rules
5. IF the file format is unrecognized THEN the system SHALL display an error message indicating the unsupported format
6. WHEN data is parsed THEN the system SHALL tag each record with its detected source

### Requirement 3

**User Story:** As a user, I want to paste CSV data directly into a text area, so that I can quickly process data without uploading files.

#### Acceptance Criteria

1. WHEN a user accesses the manual input section THEN the system SHALL display a text area for CSV data entry
2. WHEN CSV data is pasted into the text area THEN the system SHALL validate the format
3. WHEN the user clicks "Process Data" THEN the system SHALL parse the pasted CSV data
4. IF the pasted data is invalid CSV format THEN the system SHALL display validation errors
5. WHEN manual data is processed THEN the system SHALL apply the same automatic source detection as file uploads

### Requirement 4

**User Story:** As a user, I want to filter income data by date range and source type, so that I can analyze specific periods and platforms.

#### Acceptance Criteria

1. WHEN data is loaded THEN the system SHALL display date range filter controls (start date and end date)
2. WHEN data is loaded THEN the system SHALL display a dropdown filter for source types (All, Izipay, Culqi, Sirvoy)
3. WHEN date filters are applied THEN the system SHALL show only transactions within the specified date range
4. WHEN source type filter is applied THEN the system SHALL show only transactions from the selected source
5. WHEN filters are cleared THEN the system SHALL display all loaded data
6. WHEN filters are applied THEN the system SHALL update all totals and calculations accordingly

### Requirement 5

**User Story:** As a user, I want to see total income calculations by platform and overall, so that I can understand my revenue streams.

#### Acceptance Criteria

1. WHEN data is processed THEN the system SHALL calculate total income for each detected source (Izipay, Culqi, Sirvoy)
2. WHEN data is processed THEN the system SHALL calculate the overall total income across all sources
3. WHEN filters are applied THEN the system SHALL recalculate totals based on filtered data
4. WHEN totals are displayed THEN the system SHALL format amounts with appropriate currency symbols
5. WHEN no data is loaded THEN the system SHALL display zero totals

### Requirement 6

**User Story:** As a business owner, I want to add and manage additional operational costs, so that I can calculate accurate net profit.

#### Acceptance Criteria

1. WHEN accessing the costs section THEN the system SHALL display an input form for cost description and amount
2. WHEN a user adds a cost THEN the system SHALL validate that the amount is a positive number
3. WHEN a cost is added THEN the system SHALL display it in a list of additional costs
4. WHEN a user wants to remove a cost THEN the system SHALL provide a delete option for each cost item
5. WHEN costs are modified THEN the system SHALL automatically recalculate the total additional costs
6. WHEN costs are added or removed THEN the system SHALL update the net profit calculation

### Requirement 7

**User Story:** As a user, I want to see a comprehensive financial summary with net profit calculation, so that I can understand my overall financial performance.

#### Acceptance Criteria

1. WHEN data and costs are processed THEN the system SHALL display total income from all sources
2. WHEN data and costs are processed THEN the system SHALL display total additional costs
3. WHEN calculations are performed THEN the system SHALL compute net profit as (total income - total costs)
4. WHEN financial summary is displayed THEN the system SHALL clearly show income, costs, and net profit
5. IF net profit is negative THEN the system SHALL highlight this as a loss
6. WHEN any data changes THEN the system SHALL automatically update the financial summary

### Requirement 8

**User Story:** As a user, I want a modern and responsive interface, so that I can use the portal effectively on different devices.

#### Acceptance Criteria

1. WHEN the portal loads THEN the system SHALL display a clean, modern interface using Tailwind CSS
2. WHEN accessed on mobile devices THEN the system SHALL adapt the layout for smaller screens
3. WHEN accessed on tablets THEN the system SHALL optimize the layout for medium-sized screens
4. WHEN accessed on desktop THEN the system SHALL utilize the full screen space effectively
5. WHEN users interact with elements THEN the system SHALL provide visual feedback (hover states, focus indicators)