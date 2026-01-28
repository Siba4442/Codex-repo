# Phase 1 Response Structure Analysis

## Overview
The Phase 1 API response contains extracted menu categories and subcategories from a PDF menu. The data is hierarchically organized by pages, categories, and subcategories.

## Complete JSON Structure

```json
{
  "restaurant_name": "String (required)",
  "pages": [
    {
      "page_number": Integer,
      "data": {
        "categories": [
          {
            "name_raw": "String - Category name",
            "subcategories": [
              {
                "name_raw": "String - Subcategory name"
              }
            ]
          }
        ]
      }
    }
  ]
}
```

## Detailed Field Descriptions

### Root Level
- **restaurant_name** (string): The name of the restaurant being processed
  - Example: `"Amici Restaurant"`

### Pages Array
- **pages** (array): List of pages from the PDF menu
  - Multiple pages handled independently

### Page Object
- **page_number** (integer): The page number in the original PDF
  - Example: `1, 2, 3...`
- **data** (object): Container for extracted page content

### Data Object
- **categories** (array): List of all menu categories on that page
  - Example: `"FOOD TO SHARE"`, `"MAINS"`, `"CLASSIC PIZZA"`

### Category Object
- **name_raw** (string): The raw extracted category name from the PDF
  - Example: `"FOOD TO SHARE"`
- **subcategories** (array): List of subcategories under this category
  - Can be empty `[]` if category has no subdivisions
  - Example: For "FOOD TO SHARE" → `["Bread & Toppas", "Entrees"]`

### Subcategory Object
- **name_raw** (string): The raw extracted subcategory name
  - Example: `"Bread & Toppas"`, `"Entrees"`

## Real Example

```json
{
  "restaurant_name": "Amici Restaurant",
  "pages": [
    {
      "page_number": 1,
      "data": {
        "categories": [
          {
            "name_raw": "FOOD TO SHARE",
            "subcategories": [
              { "name_raw": "Bread & Toppas" },
              { "name_raw": "Entrees" }
            ]
          },
          {
            "name_raw": "MAINS",
            "subcategories": []
          },
          {
            "name_raw": "CLASSIC PIZZA",
            "subcategories": []
          }
        ]
      }
    }
  ]
}
```

## Frontend Editing Features

The `categories.html` interface now supports:

### Category Level
- ✅ Edit category name
- ✅ Delete entire category
- ✅ Add new category to page

### Subcategory Level
- ✅ View all subcategories under a category
- ✅ Edit subcategory name
- ✅ Delete subcategory
- ✅ Add new subcategory to a category

## Data Flow

1. **PDF Upload** → `POST /api/phase1/extract`
2. **Response** → Phase 1 structure (as above)
3. **User Review** → Edit categories/subcategories in `categories.html`
4. **Save Edits** → `PUT /api/phase1/{job_id}`
5. **Next Phase** → Proceed to Phase 2 (item extraction)

## Dirty State Tracking

The frontend tracks if any changes were made:
- Changes are marked as "dirty"
- Only dirty data is saved to avoid unnecessary updates
- Shows status message "Saving reviewed categories..." when persisting changes

## Backend Response Format

API endpoint: `POST /api/phase1/extract`

```json
{
  "job_id": "String - Unique job identifier",
  "data": { /* Phase 1 structure as above */ }
}
```

The response includes both the job_id and the extracted data for immediate frontend use.
