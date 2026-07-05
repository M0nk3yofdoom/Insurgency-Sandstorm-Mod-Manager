# Insurgency Sandstorm Mods Database Schema Analysis

## Database Structure

### Tables

#### 1. `mods`
- **Primary Key**: `id` (TEXT)
- **Columns**:
  - `id` (TEXT) - Primary key
  - `never_retry_category` (TEXT)
  - `never_retry_code` (TEXT)
  - `path_on_disk` (TEXT)
  - `date_added` (TEXT)
  - `date_live` (TEXT)
  - `date_updated` (TEXT)
  - `description` (TEXT)
  - `description_plaintext` (TEXT)

#### 2. `mod_metadata`
- **Primary Key**: `id` (INTEGER, AUTOINCREMENT)
- **Columns**:
  - `id` (INTEGER, AUTOINCREMENT) - Primary key
  - `mod_id` (TEXT) - Foreign key referencing `mods.id`
  - `mod_type` (TEXT) - Type of mod (Map, Scenario, Mutator, Other)
  - `mod_value` (TEXT) - String value for the mod metadata

## Relationships

### Primary Relationships

1. **mods ↔ mod_metadata**
   - Relationship: One-to-Many
   - Foreign Key: `mod_metadata.mod_id` → `mods.id`
   - Description: Each mod can have multiple metadata entries, but each metadata entry belongs to exactly one mod

### Data Organization

The database organizes mod information as follows:
- **mods table**: Contains base information about each mod (ID, paths, dates, descriptions)
- **mod_metadata table**: Contains type information and metadata values for each mod

### Mod Types in Database

The `mod_metadata.mod_type` field contains values that indicate the type of mod:
- "Map" - Maps
- "Scenario" - Scenarios
- "Mutator" - Mutators
- "Other" - Other types

This structure allows for a single mod to potentially have multiple types (as indicated by the GROUP BY in the original code) but each entry is specifically categorized by type.

## Implementation Notes

The console generator application:
- Uses the `mod_metadata.mod_type` field to categorize mods into Maps, Scenarios, and Mutators
- Retrieves mod names from the `mods.description` field (first line)
- Uses the `mods.id` as both identifier and display value
- Maintains one-to-many relationships between mods and their metadata