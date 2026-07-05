import webview
import sys
import os
import json
from datetime import datetime
import sqlite3

# For PyWebView function calling
import threading
import time

# 1. PORTABILITY: Use the directory of the script itself
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "state.json")
DB_PATH = os.path.join(BASE_DIR, "mods.db")

def init_database():
    """Initialize the SQLite database with proper schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create mods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mods (
            id TEXT PRIMARY KEY,
            never_retry_category TEXT,
            never_retry_code TEXT,
            path_on_disk TEXT,
            date_added TEXT,
            date_live TEXT,
            date_updated TEXT,
            description TEXT,
            description_plaintext TEXT
        )
    ''')
    
    # Create mod_metadata table for metadata relationships (new schema)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mod_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mod_id TEXT NOT NULL,
            mod_type TEXT NOT NULL,
            mod_value TEXT NOT NULL,
            FOREIGN KEY (mod_id) REFERENCES mods(id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes for efficient searching
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_metadata_mod_id ON mod_metadata(mod_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_metadata_mod_type ON mod_metadata(mod_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_metadata_mod_value ON mod_metadata(mod_value);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_metadata_mod_id_type ON mod_metadata(mod_id, mod_type);")
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

def load_and_process():
    """Parse JSON and transform data for the frontend."""
    # Check if database exists and has data
    if os.path.exists(DB_PATH):
        # Check if database has data
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM mods')
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print("Loading data from database")
            return load_from_db()
    
    # If database doesn't exist or is empty, load from JSON
    if not os.path.exists(JSON_PATH):
        print(f"Warning: {JSON_PATH} not found.")
        return []
    
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading JSON: {e}")
        return []

    # Extract mods from the data structure
    mods = data.get("Mods", [])
    
    processed = []
    for mod in mods:
        if isinstance(mod, str):
            try:
                mod = json.loads(mod)
            except json.JSONDecodeError:
                continue

        # Helper function to format date from Unix timestamp
        def format_date(timestamp):
            if timestamp and isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return "N/A"

        # Extract all available fields including nested sections
        processed.append({
            "id": str(mod.get("ID", "N/A")),
            "never_retry_category": mod.get("NeverRetryCategory", "N/A"),
            "never_retry_code": mod.get("NeverRetryCode", "N/A"),
            "path_on_disk": mod.get("PathOnDisk", "N/A"),
            "date_added": format_date(mod.get("Profile", {}).get("date_added")),
            "date_live": format_date(mod.get("Profile", {}).get("date_live")),
            "date_updated": format_date(mod.get("Profile", {}).get("date_updated")),
            "description": mod.get("Profile", {}).get("description", "N/A"),
            "description_plaintext": mod.get("Profile", {}).get("description_plaintext", "N/A"),
        })
    
    # Save to database immediately after processing
    save_to_db(processed)
    return processed


def load_from_db():
    """Load data from SQLite database file."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all mods
        cursor.execute('SELECT * FROM mods')
        mods = cursor.fetchall()
        
        # Convert to proper format
        result = []
        for mod in mods:
            mod_dict = {
                "id": mod[0],
                "never_retry_category": mod[1],
                "never_retry_code": mod[2],
                "path_on_disk": mod[3],
                "date_added": mod[4],
                "date_live": mod[5],
                "date_updated": mod[6],
                "description": mod[7],
                "description_plaintext": mod[8]
            }
            result.append(mod_dict)
        
        conn.close()
        return result
    except Exception as e:
        print(f"Error loading from database: {e}")
        return []


def save_to_db(mods):
    """Save processed data to SQLite database file."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Clear existing data from mods table only (let CASCADE delete handle mod_metadata)
        cursor.execute('DELETE FROM mods')
        
        # Insert mods
        for mod in mods:
            cursor.execute('''
                INSERT OR REPLACE INTO mods 
                (id, never_retry_category, never_retry_code, path_on_disk, 
                 date_added, date_live, date_updated, description, description_plaintext)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mod["id"],
                mod["never_retry_category"],
                mod["never_retry_code"],
                mod["path_on_disk"],
                mod["date_added"],
                mod["date_live"],
                mod["date_updated"],
                mod["description"],
                mod["description_plaintext"]
            ))
        
        conn.commit()
        conn.close()
        print("Data saved to database")
    except Exception as e:
        print(f"Error saving to database: {e}")


def merge_json_with_xml():
    """Merge data from state.json with database, updating existing entries and adding new ones."""
    print("DEBUG: Starting merge_json_with_xml function")
    
    # First load the existing database data
    xml_data = load_from_db()
    print(f"DEBUG: Loaded {len(xml_data)} mods from database")
    
    # Then load the JSON data
    if not os.path.exists(JSON_PATH):
        print(f"Warning: {JSON_PATH} not found.")
        return xml_data
    
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("DEBUG: Successfully loaded JSON file")
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading JSON: {e}")
        return xml_data

    # Extract mods from the data structure
    mods = data.get("Mods", [])
    print(f"DEBUG: Found {len(mods)} mods in JSON")
    
    processed = []
    for mod in mods:
        if isinstance(mod, str):
            try:
                mod = json.loads(mod)
            except json.JSONDecodeError:
                continue

        # Helper function to format date from Unix timestamp
        def format_date(timestamp):
            if timestamp and isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            return "N/A"

        # Extract all available fields including nested sections
        processed.append({
            "id": str(mod.get("ID", "N/A")),
            "never_retry_category": mod.get("NeverRetryCategory", "N/A"),
            "never_retry_code": mod.get("NeverRetryCode", "N/A"),
            "path_on_disk": mod.get("PathOnDisk", "N/A"),
            "date_added": format_date(mod.get("Profile", {}).get("date_added")),
            "date_live": format_date(mod.get("Profile", {}).get("date_live")),
            "date_updated": format_date(mod.get("Profile", {}).get("date_updated")),
            "description": mod.get("Profile", {}).get("description", "N/A"),
            "description_plaintext": mod.get("Profile", {}).get("description_plaintext", "N/A"),
        })
    
    print(f"DEBUG: Processed {len(processed)} mods from JSON")
    
    # Merge with existing database data
    xml_dict = {mod["id"]: mod for mod in xml_data}
    json_dict = {mod["id"]: mod for mod in processed}
    
    # Track statistics
    stats = {
        "new_mods": 0,
        "updated_mods": 0,
        "removed_mods": 0
    }
    
    print(f"DEBUG: Starting merge process. XML mods: {len(xml_dict)}, JSON mods: {len(json_dict)}")
    
    # Update existing entries or add new ones, and track what changed
    merged_data = xml_data.copy()
    for id, json_mod in json_dict.items():
        if id in xml_dict:
            # Update existing entry if description or description_plaintext changed
            xml_mod = xml_dict[id]
            if xml_mod.get("description") != json_mod.get("description") or \
               xml_mod.get("description_plaintext") != json_mod.get("description_plaintext"):
                # Keep existing ID, but update other fields (but not the ID)
                updated_mod = xml_mod.copy()
                updated_mod["description"] = json_mod["description"]
                updated_mod["description_plaintext"] = json_mod["description_plaintext"]
                # Replace the mod in merged data
                for i, mod in enumerate(merged_data):
                    if mod["id"] == id:
                        merged_data[i] = updated_mod
                        stats["updated_mods"] += 1
                        print(f"DEBUG: Updated mod {id}")
                        break
        else:
            # Add new mod from JSON
            merged_data.append(json_mod)
            stats["new_mods"] += 1
            print(f"DEBUG: Added new mod {json_mod['id']}")
    
    print(f"DEBUG: After adding new mods, have {len(merged_data)} total mods")
    
    # Remove mods that are no longer in the JSON file but exist in the database
    json_ids = set(json_dict.keys())
    xml_ids = set(xml_dict.keys())
    removed_ids = xml_ids - json_ids
    
    print(f"DEBUG: Removing {len(removed_ids)} mods that are no longer in JSON")
    
    # Remove mods that were removed from JSON
    merged_data = [mod for mod in merged_data if mod["id"] not in removed_ids]
    stats["removed_mods"] = len(removed_ids)
    
    print(f"DEBUG: Before saving, have {len(merged_data)} mods in database")
    
    # Save the merged data back to database
    save_to_db(merged_data)
    
    # Return the result with statistics
    result = {
        "data": merged_data,
        "stats": stats
    }
    # Print debug info
    print(f"DEBUG: Merge completed. Stats - New: {stats['new_mods']}, Updated: {stats['updated_mods']}, Removed: {stats['removed_mods']}")
    return result


def get_available_types():
    """Get all available types from the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Since we removed mod_types table, we'll get types from mod_metadata instead
        cursor.execute('SELECT DISTINCT mod_type FROM mod_metadata WHERE mod_type IS NOT NULL AND mod_type != ""')
        types = [row[0] for row in cursor.fetchall()]
        conn.close()
        return types
    except Exception as e:
        print(f"Error getting available types: {e}")
        return []


def get_available_tags():
    """Get all available tags from the database."""
    # Since we removed mod_tags table, this functionality is no longer needed
    return []


def add_type(type_name):
    """Add a new type to the database."""
    # Since we removed mod_types table, this functionality is no longer needed
    return True


def add_tag(tag_name):
    """Add a new tag to the database."""
    # Since we removed mod_tags table, this functionality is no longer needed
    return True


def get_mod_metadata(mod_id, filter_type='all'):
    """Get all metadata values for a specific mod."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if filter_type == 'all':
            cursor.execute('''
                SELECT mod_value FROM mod_metadata WHERE mod_id = ? ORDER BY id
            ''', (mod_id,))
        else:
            cursor.execute('''
                SELECT mod_value FROM mod_metadata WHERE mod_id = ? AND mod_type = ? ORDER BY id
            ''', (mod_id, filter_type))
        metadata = cursor.fetchall()
        conn.close()
        # Return just the values
        return [row[0] for row in metadata]
    except Exception as e:
        print(f"Error getting mod metadata: {e}")
        return []


def add_mod_metadata(mod_id, type_name, metadata_value):
    """Add a metadata pair for a specific mod."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO mod_metadata (mod_id, mod_type, mod_value) VALUES (?, ?, ?)
        ''', (mod_id, type_name, metadata_value))
        conn.commit()
        conn.close()
        print(f"Added metadata for mod {mod_id}: {type_name} -> {metadata_value}")
        return True
    except Exception as e:
        print(f"Error adding mod metadata: {e}")
        return False


def get_all_metadata(filter_type='all'):
    """Get all metadata values in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if filter_type == 'all':
            cursor.execute('''
                SELECT mod_value FROM mod_metadata ORDER BY id
            ''')
        else:
            cursor.execute('''
                SELECT mod_value FROM mod_metadata WHERE mod_type = ? ORDER BY id
            ''', (filter_type,))
        metadata = cursor.fetchall()
        conn.close()
        # Return just the values
        return [row[0] for row in metadata]
    except Exception as e:
        print(f"Error getting all metadata: {e}")
        return []


class DatabaseAPI:
    """Database API for PyWebView to communicate with SQLite database."""
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def load_from_db(self):
        """Load data from SQLite database file."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all mods
            cursor.execute('SELECT * FROM mods')
            mods = cursor.fetchall()
            
            # Convert to proper format
            result = []
            for mod in mods:
                mod_dict = {
                    "id": mod[0],
                    "never_retry_category": mod[1],
                    "never_retry_code": mod[2],
                    "path_on_disk": mod[3],
                    "date_added": mod[4],
                    "date_live": mod[5],
                    "date_updated": mod[6],
                    "description": mod[7],
                    "description_plaintext": mod[8]
                }
                result.append(mod_dict)
            
            conn.close()
            import sys
            print(f"DEBUG: load_from_db completed, loaded {len(result)} mods")
            sys.stdout.flush()
            return result
        except Exception as e:
            print(f"Error loading from database: {e}")
            sys.stdout.flush()
            return []
    
    def save_to_db(self, mods):
        """Save processed data to SQLite database file."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing data from mods table only (let CASCADE delete handle mod_metadata)
            cursor.execute('DELETE FROM mods')
            
            # Insert mods
            for mod in mods:
                cursor.execute('''
                    INSERT OR REPLACE INTO mods 
                    (id, never_retry_category, never_retry_code, path_on_disk, 
                     date_added, date_live, date_updated, description, description_plaintext)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    mod["id"],
                    mod["never_retry_category"],
                    mod["never_retry_code"],
                    mod["path_on_disk"],
                    mod["date_added"],
                    mod["date_live"],
                    mod["date_updated"],
                    mod["description"],
                    mod["description_plaintext"]
                ))
            
            conn.commit()
            conn.close()
            import sys
            print("DEBUG: Data saved to database")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error saving to database: {e}")
            sys.stdout.flush()
    
    def merge_json_with_xml(self):
        """Merge data from state.json with database, updating existing entries and adding new ones."""
        # Print to both webview console and terminal
        import sys
        debug_msg = "DEBUG: merge_json_with_xml called from JavaScript API"
        print(debug_msg)
        sys.stdout.flush()  # Ensure output is visible
        
        # Import the module level function to access it
        import insurgency_manager
        # First load the existing database data using the module function
        xml_data = insurgency_manager.load_from_db()
        debug_msg = f"DEBUG: Loaded {len(xml_data)} mods from database"
        print(debug_msg)
        sys.stdout.flush()
        
        # Then load the JSON data
        if not os.path.exists(JSON_PATH):
            debug_msg = f"Warning: {JSON_PATH} not found."
            print(debug_msg)
            sys.stdout.flush()
            return xml_data
        
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            debug_msg = "DEBUG: Successfully loaded JSON file"
            print(debug_msg)
            sys.stdout.flush()
        except (json.JSONDecodeError, IOError) as e:
            debug_msg = f"Error loading JSON: {e}"
            print(debug_msg)
            sys.stdout.flush()
            return xml_data

        # Extract mods from the data structure
        mods = data.get("Mods", [])
        debug_msg = f"DEBUG: Found {len(mods)} mods in JSON"
        print(debug_msg)
        sys.stdout.flush()
        
        processed = []
        for mod in mods:
            if isinstance(mod, str):
                try:
                    mod = json.loads(mod)
                except json.JSONDecodeError:
                    continue

            # Helper function to format date from Unix timestamp
            def format_date(timestamp):
                if timestamp and isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                return "N/A"

            # Extract all available fields including nested sections
            processed.append({
                "id": str(mod.get("ID", "N/A")),
                "never_retry_category": mod.get("NeverRetryCategory", "N/A"),
                "never_retry_code": mod.get("NeverRetryCode", "N/A"),
                "path_on_disk": mod.get("PathOnDisk", "N/A"),
                "date_added": format_date(mod.get("Profile", {}).get("date_added")),
                "date_live": format_date(mod.get("Profile", {}).get("date_live")),
                "date_updated": format_date(mod.get("Profile", {}).get("date_updated")),
                "description": mod.get("Profile", {}).get("description", "N/A"),
                "description_plaintext": mod.get("Profile", {}).get("description_plaintext", "N/A"),
            })
        
        debug_msg = f"DEBUG: Processed {len(processed)} mods from JSON"
        print(debug_msg)
        sys.stdout.flush()
        
        # Merge with existing database data
        xml_dict = {mod["id"]: mod for mod in xml_data}
        json_dict = {mod["id"]: mod for mod in processed}
        
        # Track statistics
        stats = {
            "new_mods": 0,
            "updated_mods": 0,
            "removed_mods": 0
        }
        
        debug_msg = f"DEBUG: Starting merge process. XML mods: {len(xml_dict)}, JSON mods: {len(json_dict)}"
        print(debug_msg)
        sys.stdout.flush()
        
        # Update existing entries or add new ones, and track what changed
        merged_data = xml_data.copy()
        for id, json_mod in json_dict.items():
            if id in xml_dict:
                # Update existing entry if description or description_plaintext changed
                xml_mod = xml_dict[id]
                if xml_mod.get("description") != json_mod.get("description") or \
                   xml_mod.get("description_plaintext") != json_mod.get("description_plaintext"):
                    # Keep existing ID, but update other fields (but not the ID)
                    updated_mod = xml_mod.copy()
                    updated_mod["description"] = json_mod["description"]
                    updated_mod["description_plaintext"] = json_mod["description_plaintext"]
                    # Replace the mod in merged data
                    for i, mod in enumerate(merged_data):
                        if mod["id"] == id:
                            merged_data[i] = updated_mod
                            stats["updated_mods"] += 1
                            debug_msg = f"DEBUG: Updated mod {id}"
                            print(debug_msg)
                            sys.stdout.flush()
                            break
            else:
                # Add new mod from JSON
                merged_data.append(json_mod)
                stats["new_mods"] += 1
                debug_msg = f"DEBUG: Added new mod {json_mod['id']}"
                print(debug_msg)
                sys.stdout.flush()
        
        debug_msg = f"DEBUG: After adding new mods, have {len(merged_data)} total mods"
        print(debug_msg)
        sys.stdout.flush()
        
        # Remove mods that are no longer in the JSON file but exist in the database
        json_ids = set(json_dict.keys())
        xml_ids = set(xml_dict.keys())
        removed_ids = xml_ids - json_ids
        
        debug_msg = f"DEBUG: Removing {len(removed_ids)} mods that are no longer in JSON"
        print(debug_msg)
        sys.stdout.flush()
        
        # Remove mods that were removed from JSON
        merged_data = [mod for mod in merged_data if mod["id"] not in removed_ids]
        stats["removed_mods"] = len(removed_ids)
        
        debug_msg = f"DEBUG: Before saving, have {len(merged_data)} mods in database"
        print(debug_msg)
        sys.stdout.flush()
        
        # Save the merged data back to database
        self.save_to_db(merged_data)
        
        # Return the result with statistics
        result = {
            "data": merged_data,
            "stats": stats
        }
        # Print debug info
        debug_msg = f"DEBUG: Merge completed. Stats - New: {stats['new_mods']}, Updated: {stats['updated_mods']}, Removed: {stats['removed_mods']}"
        print(debug_msg)
        sys.stdout.flush()
        return result
    
    def get_mod_metadata(self, mod_id, filter_type='all'):
        """Get all metadata values for a specific mod."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if filter_type == 'all':
                cursor.execute('''
                    SELECT id, mod_type, mod_value FROM mod_metadata WHERE mod_id = ? ORDER BY id
                ''', (mod_id,))
            else:
                cursor.execute('''
                    SELECT id, mod_type, mod_value FROM mod_metadata WHERE mod_id = ? AND mod_type = ? ORDER BY id
                ''', (mod_id, filter_type))
            metadata = cursor.fetchall()
            conn.close()
            # Return list of dictionaries with id, type and metadata
            return [{'id': row[0], 'type': row[1], 'metadata': row[2]} for row in metadata]
        except Exception as e:
            print(f"Error getting mod metadata: {e}")
            return [{"error": str(e)}]
    
    def add_mod_metadata(self, mod_id, type_name, metadata_value):
        """Add a metadata pair for a specific mod."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mod_metadata (mod_id, mod_type, mod_value) VALUES (?, ?, ?)
            ''', (mod_id, type_name, metadata_value))
            conn.commit()
            conn.close()
            import sys
            print(f"DEBUG: Added metadata for mod {mod_id}: {type_name} -> {metadata_value}")
            sys.stdout.flush()
            return {"success": True}
        except Exception as e:
            print(f"Error adding mod metadata: {e}")
            sys.stdout.flush()
            return {"error": str(e)}
    
    def get_all_metadata(self, filter_type='all'):
        """Get all metadata values in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if filter_type == 'all':
                cursor.execute('''
                    SELECT id, mod_type, mod_value FROM mod_metadata ORDER BY id
                ''')
            else:
                cursor.execute('''
                    SELECT id, mod_type, mod_value FROM mod_metadata WHERE mod_type = ? ORDER BY id
                ''', (filter_type,))
            metadata = cursor.fetchall()
            conn.close()
            # Return list of dictionaries with id, type and metadata
            return [{'id': row[0], 'type': row[1], 'metadata': row[2]} for row in metadata]
        except Exception as e:
            print(f"Error getting all metadata: {e}")
            return [{"error": str(e)}]
    
    def delete_metadata(self, metadata_id):
        """Delete a specific metadata entry by ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM mod_metadata WHERE id = ?
            ''', (metadata_id,))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            print(f"Error deleting metadata: {e}")
            return {"error": str(e)}

def start_manager():
    mod_data = load_and_process()
    sort_config = {"key": "id", "direction": "asc"}

    # Prepare data for injection
    mods_json = json.dumps(mod_data)
    sort_json = json.dumps(sort_config)

    # 3. STABILITY: Using a plain string for the template to avoid f-string/JS {} conflicts
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insurgency:Sandstorm MOD.IO Manager</title>
        <style>
            :root {
                --bg: #171317;
                --surface: #2a2525;
                --accent: #DDBFA2;
                --text: #858F8B;
                --error: #AB381C;
                --border-radius: 4px;
            }

            body {
                background: var(--bg);
                color: var(--text);
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                display: flex;
                flex-direction: column;
                height: 100vh;
                overflow: hidden;
                position: relative;
            }

            header {
                background: var(--surface);
                padding: 1rem 2rem;
                border-bottom: 1px solid #333;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            h1 { 
                margin: 0; 
                font-size: 1.5rem; 
                color: var(--accent); 
                text-transform: uppercase;
                font-weight: bold;
            }

            .search-bar { 
                margin: 1.5rem 2rem;
                display: flex;
                gap: 1rem;
                align-items: center;
            }

            #search-input {
                flex: 1;
                max-width: 600px;
                padding: 12px 16px;
                background: var(--surface);
                border: 2px solid #333;
                border-radius: 0; /* Sharp edges */
                color: var(--text);
                font-size: 1rem;
                transition: border-color 0.2s;
            }

            #search-input:focus { outline: none; border-color: var(--accent); }

            #reimport-btn {
                margin-left: 1rem;
            }

            .main-container {
                display: flex;
                flex-grow: 1;
                overflow: hidden;
                margin: 0 2rem 2rem;
            }

            .table-container {
                flex: 1;
                overflow: auto;
                border-radius: var(--border-radius);
                border: 1px solid #333;
            }

            .details-container {
                width: 50%;
                background: var(--surface);
                border: 1px solid #333;
                border-radius: var(--border-radius);
                margin-left: 1rem;
                padding: 1rem;
                overflow: auto;
                display: none;
            }

            .details-container.active {
                display: block;
            }
            
            .metadata-panel {
                background: var(--surface);
                border: 1px solid #333;
                border-radius: var(--border-radius);
                width: 33%;
                height: 40%;
                position: absolute;
                left: 2rem;
                bottom: 2rem;
                padding: 1rem;
                overflow: auto;
                z-index: 1000;
                display: none;
            }
            
            .metadata-panel input, .metadata-panel select {
                background: var(--surface);
                color: var(--text);
                border: 1px solid #444;
            }
            
            .metadata-panel input {
                padding: 8px;
                border-radius: 0;
                background: var(--surface);
                color: var(--text);
            }
            
            .metadata-panel select {
                padding: 8px;
                border-radius: 0;
                background: var(--surface);
                color: var(--text);
            }
            
            .metadata-panel input {
                padding: 8px;
                border-radius: 0;
            }
            
            .metadata-panel select {
                padding: 8px;
                border-radius: 0;
            }

            table { width: 100%; border-collapse: collapse; text-align: left; }

            th {
                position: sticky;
                top: 0;
                background: #DDBFA2;
                padding: 14px;
                border-bottom: 2px solid #444;
                cursor: pointer;
                user-select: none;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                border-radius: var(--border-radius);
                color: var(--text); /* Ensure text is visible in both themes */
            }

            th:hover { 
                background: #2c2c2c; 
                color: var(--text); /* Ensure text is visible in both themes */
            }

            td { padding: 2px 4px; border-bottom: 1px solid #333; font-size: 0.7rem; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text; }

            tbody tr:hover { background: #f5f5f5; }

            tbody tr.selected {
                background: #e8e8e8;
                font-weight: bold;
            }

            .badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: bold;
                text-transform: uppercase;
                display: inline-block;
            }

            ::-webkit-scrollbar { width: 8px; }
            ::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
            
            .theme-toggle-btn {
                background: var(--surface);
                color: var(--text);
                border: 1px solid #333;
                border-radius: 0; /* Sharp edges */
                width: 40px;
                height: 40px;
                cursor: pointer;
                font-size: 1.2rem;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .theme-toggle-btn:hover {
                background: #333;
            }
            
            .status-bar {
                background: var(--surface);
                padding: 0.5rem 2rem;
                border-top: 1px solid #333;
                font-size: 0.8rem;
                display: flex;
                justify-content: space-between;
            }
            
            /* Apply consistent button styling */
            #reimport-btn, #metadata-toggle-btn, #add-metadata-btn, #delete-selected-btn {
                padding: 12px 20px;
                background: var(--accent);
                color: var(--bg);
                border: none;
                border-radius: 0; /* Sharp edges */
                cursor: pointer;
                font-weight: bold;
                transition: background 0.2s;
                min-width: 120px;
                height: 40px;
                font-size: 1rem;
                margin: 0 4px;
            }
            
            #reimport-btn:hover, #metadata-toggle-btn:hover, #add-metadata-btn:hover, #delete-selected-btn:hover {
                background: #9a68d0;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>INSURGENCY:SANDSTORM MOD.IO MANAGER</h1>
            <button id="theme-toggle-btn" class="theme-toggle-btn">🌙</button>
        </header>
        <div class="search-bar">
            <input id="search-input" placeholder="Search mods by any field..." autocomplete="off">
            <button id="reimport-btn" class="btn">Reimport JSON</button>
            <button id="metadata-toggle-btn" class="btn">Manage Metadata</button>
        </div>
        <div class="main-container">
            <div class="table-container">
                <table id="mod-table">
                    <thead>
                    <tr>
                        <th data-sort="id">ID</th>
                        <th data-sort="path_on_disk">Path On Disk</th>
                        <th data-sort="date_added">Date Added</th>
                        <th data-sort="date_live">Date Live</th>
                        <th data-sort="date_updated">Date Updated</th>
                        <th data-sort="description">Description</th>
                        <th data-sort="description_plaintext">Description (Plain)</th>
                    </tr>
                    </thead>
                    <tbody id="mod-tbody"></tbody>
                </table>
            </div>
            <div class="details-container" id="details-container">
                <h2 id="detail-title">Mod Details</h2>
                <div id="detail-content"></div>
            </div>
        </div>
        
        <!-- Metadata Management Panel -->
        <div id="metadata-panel" class="metadata-panel">
            <h3>Metadata Management</h3>
            <div id="metadata-input-section" style="margin-bottom: 1rem; display: none;">
                <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                    <div style="flex: 1;">
                        <label for="metadata-type-select">Type:</label>
                        <select id="metadata-type-select" style="width: 100%; padding: 8px; background: var(--surface); border: 1px solid #444; border-radius: 0; color: var(--text); height: 40px;">
                            <option value="Map">Map</option>
                            <option value="Scenario">Scenario</option>
                            <option value="Mutator">Mutator</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                    <div style="flex: 4;">
                        <label for="metadata-value-input">Metadata Value:</label>
                        <input type="text" id="metadata-value-input" placeholder="Enter metadata value" style="width: 90%; padding: 8px; background: #DDBFA2; border: 1px solid #444; border-radius: 0; color: white; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text;">
                    </div>
                        <div style="flex: 1; display: flex; align-items: flex-end;">
                            <button id="add-metadata-btn" class="btn" style="font-size: 0.8rem; padding: 6px 12px;">Add Metadata</button>
                        </div>
                </div>
            </div>
            
            <div id="metadata-display-section">
                <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem; align-items: center; justify-content: space-between;">
                    <h4 id="metadata-title">All Metadata Pairs</h4>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <select id="metadata-filter-select" style="padding: 6px; background: #DDBFA2; border: 1px solid #444; border-radius: 0; color: white; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text; font-size: 0.8rem; height: 40px;">
                            <option value="all">Filter</option>
                            <option value="Map">Map</option>
                            <option value="Scenario">Scenario</option>
                            <option value="Mutator">Mutator</option>
                            <option value="Other">Other</option>
                        </select>
                        <input type="checkbox" id="delete-mode-checkbox" style="width: 16px; height: 16px; border-radius: var(--border-radius);">
                        <label for="delete-mode-checkbox" style="margin: 0; font-size: 0.8rem;">Enable Delete Mode</label>
                        <button id="delete-selected-btn" class="btn" style="display: none; font-size: 0.8rem; padding: 6px 12px; border-radius: var(--border-radius);">Delete Selected</button>
                    </div>
                </div>
                <div id="metadata-content" style="background: var(--surface); border: 1px solid #444; border-radius: 4px; padding: 0.5rem; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text; overflow: auto; display: block; width: 95%;">
                    <i>Loading metadata...</i>
                </div>
            </div>
        </div>

        <div class="status-bar">
            <div id="status-text">Server Mode Connected</div>
            <div id="last-updated">Last updated: --</div>
        </div>

        <script>
            let mods = MODS_DATA;
            let sortConfig = SORT_CONFIG;
            let filteredMods = [...mods];
            let selectedModId = null;
            let lastUpdate = new Date();
            let isDarkTheme = true;

            // Wait for pywebview to be ready
            window.addEventListener('pywebviewready', function() {
                console.log('pywebview is ready - functions available');
                loadAllMetadata();
            });

            // Theme toggle functionality
            document.getElementById('theme-toggle-btn').addEventListener('click', function() {
                isDarkTheme = !isDarkTheme;
                updateTheme();
            });

            function updateTheme() {
                const root = document.documentElement;
                if (isDarkTheme) {
                    // Dark theme
                    root.style.setProperty('--bg', '#171317');
                    root.style.setProperty('--surface', '#2a2525');
                    root.style.setProperty('--accent', '#DDBFA2');
                    root.style.setProperty('--text', '#858F8B');
                    root.style.setProperty('--error', '#AB381C');
                    document.getElementById('theme-toggle-btn').textContent = '🌙';
                    // For dark theme, we want white text in textboxes
                    document.querySelectorAll('input, select').forEach(el => {
                        if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                            el.style.color = 'white';
                            el.style.backgroundColor = '#2a2525';
                        }
                    });
                } else {
                    // Light theme
                    root.style.setProperty('--bg', '#ffffff');
                    root.style.setProperty('--surface', '#f0f0f0');
                    root.style.setProperty('--accent', '#6C4534');
                    root.style.setProperty('--text', '#333333');
                    root.style.setProperty('--error', '#AB381C');
                    document.getElementById('theme-toggle-btn').textContent = '☀️';
                    // For light theme, we want dark text in textboxes
                    document.querySelectorAll('input, select').forEach(el => {
                        if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                            el.style.color = '#333333';
                            el.style.backgroundColor = '#ffffff';
                        }
                    });
                }
            }

            // Initialize theme
            updateTheme();
            
            // Set initial text colors for input elements
            document.querySelectorAll('input, select').forEach(el => {
                if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                    if (isDarkTheme) {
                        el.style.color = 'white';
                    } else {
                        el.style.color = '#333333';
                    }
                }
            });
            
            // Set initial timestamp
            updateLastUpdated();

             function updateLastUpdated() {
                const now = new Date();
                lastUpdate = now;
                // Format as "14:35 4 Mar 2026"
                const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: false };
                const dateOptions = { day: 'numeric', month: 'short', year: 'numeric' };
                const timeString = now.toLocaleTimeString('en-US', timeOptions);
                const dateString = now.toLocaleDateString('en-US', dateOptions);
                document.getElementById('last-updated').textContent = 
                    'Last updated: ' + timeString + ' ' + dateString;
            }

            function render() {
                const tbody = document.getElementById('mod-tbody');
                tbody.innerHTML = '';

                const sortKey = sortConfig.key;
                const direction = sortConfig.direction;

                filteredMods.sort((a, b) => {
                    let valA = a[sortKey];
                    let valB = b[sortKey];

                    if (typeof valA === 'string') valA = valA.toLowerCase();
                    if (typeof valB === 'string') valB = valB.toLowerCase();

                    if (valA < valB) return direction === 'asc' ? -1 : 1;
                    if (valA > valB) return direction === 'asc' ? 1 : -1;
                    return 0;
                });

                filteredMods.forEach((mod, index) => {
                    const tr = document.createElement('tr');
                    tr.dataset.index = index;
                    
                    // Truncate long description for display
                    const truncatedDesc = mod.description.length > 100 ? mod.description.substring(0, 100) + '...' : mod.description;
                    const truncatedPlain = mod.description_plaintext.length > 100 ? mod.description_plaintext.substring(0, 100) + '...' : mod.description_plaintext;

                    tr.innerHTML = `
                        <td>${mod.id}</td>
                        <td>${mod.path_on_disk}</td>
                        <td>${mod.date_added}</td>
                        <td>${mod.date_live}</td>
                        <td>${mod.date_updated}</td>
                        <td style="white-space: pre-wrap; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text;">${truncatedDesc}</td>
                        <td style="white-space: pre-wrap; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text;">${truncatedPlain}</td>
                    `;
                    tbody.appendChild(tr);
                    
                    // Create a single row with expandable content inside
                    const expandableRow = document.createElement('tr');
                    expandableRow.dataset.index = index;
                    expandableRow.className = 'expandable-row';
                    expandableRow.innerHTML = `
                        <td colspan="9" class="expandable-row-content" style="display: none;">
                            <h3>Full Description</h3>
                            <pre>${mod.description}</pre>
                            <h3>Full Description (Plain)</h3>
                            <pre>${mod.description_plaintext}</pre>
                        </td>
                    `;
                    tbody.appendChild(expandableRow);
                });
            }

            function handleSort(e) {
                const key = e.target.dataset.sort;
                if (!key) return;
                if (sortConfig.key === key) {
                    sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    sortConfig.key = key;
                    sortConfig.direction = 'asc';
                }
                render();
            }

            document.querySelectorAll('th[data-sort]').forEach(th => th.addEventListener('click', handleSort));

            document.getElementById('search-input').addEventListener('input', e => {
                const q = e.target.value.toLowerCase();
                filteredMods = mods.filter(m => {
                    return m.id.toLowerCase().includes(q) ||
                            m.path_on_disk.toLowerCase().includes(q) ||
                            m.date_added.toLowerCase().includes(q) ||
                            m.date_live.toLowerCase().includes(q) ||
                            m.date_updated.toLowerCase().includes(q) ||
                            m.description.toLowerCase().includes(q) ||
                            m.description_plaintext.toLowerCase().includes(q);
                });
                render();
            });

            // Add click handler for expanding rows
            document.getElementById('mod-tbody').addEventListener('click', function(e) {
                // Check if clicked on a data row (not an expandable row)
                const row = e.target.closest('tr');
                if (row && row.dataset.index !== undefined) {
                    const index = row.dataset.index;
                    // Find the next sibling row which should be the expandable content row
                    const nextRow = row.nextElementSibling;
                    if (nextRow && nextRow.classList.contains('expandable-row')) {
                        // Toggle visibility of the expandable content
                        if (nextRow.style.display === 'none') {
                            nextRow.style.display = 'table-row';
                        } else {
                            nextRow.style.display = 'none';
                        }
                    }
                }
            });

            // Add click handler for selecting rows
            document.getElementById('mod-tbody').addEventListener('click', function(e) {
                const row = e.target.closest('tr');
                if (row && row.dataset.index !== undefined) {
                    const index = row.dataset.index;
                    
                    // Check if clicking the same row that's already selected
                    if (row.classList.contains('selected')) {
                        // Unselect the row and hide details
                        row.classList.remove('selected');
                        document.getElementById('details-container').classList.remove('active');
                        // Hide the metadata input section when no mod is selected
                        document.getElementById('metadata-input-section').style.display = 'none';
                        document.getElementById('metadata-title').textContent = 'All Metadata Pairs';
                        loadAllMetadata();
                    } else {
                        // Remove selected class from all rows
                        document.querySelectorAll('#mod-tbody tr').forEach(r => {
                            r.classList.remove('selected');
                        });
                        
                        // Add selected class to clicked row
                        row.classList.add('selected');
                        
                        // Get the mod data for this row
                        const mod = filteredMods[index];
                        selectedModId = mod.id; // Set the selected mod ID
                        
                        // Display details in the side panel
                        const detailsContainer = document.getElementById('details-container');
                        const detailTitle = document.getElementById('detail-title');
                        const detailContent = document.getElementById('detail-content');
                        
                        detailTitle.textContent = `Mod Details - ${mod.id}`;
                        detailContent.innerHTML = `
                            <div style="margin-bottom: 1rem;">
                                <h3>Full Description</h3>
                                <pre style="white-space: pre-wrap; background: var(--surface); padding: 10px; border-radius: 4px; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text;">${mod.description}</pre>
                            </div>
                            <div>
                                <h3>Full Description (Plain)</h3>
                                <pre style="white-space: pre-wrap; background: var(--surface); padding: 10px; border-radius: 4px; -webkit-user-select: text; -moz-user-select: text; -ms-user-select: text; user-select: text;">${mod.description_plaintext}</pre>
                            </div>
                        `;
                        
                        // Show the details container
                        detailsContainer.classList.add('active');
                        
                        // Show metadata input section for the selected mod
                        document.getElementById('metadata-input-section').style.display = 'block';
                        document.getElementById('metadata-title').textContent = `Assigned Metadata for Mod ${selectedModId}`;
                        loadAssignedMetadata(selectedModId);
                    }
                }
            });

            // Reimport functionality - server operation
            document.getElementById('reimport-btn').addEventListener('click', function() {
                if (confirm('This will reimport data from state.json and merge with existing data. Existing data will be preserved but descriptions may be updated. Continue?')) {
                    // Call the Python function to reimport data
                    pywebview.api.merge_json_with_xml().then(function(result) {
                        console.log('Data reimported successfully');
                        // Update the last updated timestamp
                        updateLastUpdated();
                        // Show statistics
                        const stats = result.stats;
                        alert(`Reimport completed!\nNew mods: ${stats.new_mods}\nUpdated mods: ${stats.updated_mods}\nRemoved mods: ${stats.removed_mods}`);
                        // Refresh the table (data already updated in database)
                        render();
                    }).catch(function(error) {
                        console.error('Error reimporting data:', error);
                        alert('Error reimporting data: ' + error.message);
                    });
                }
            });

            // Add click handler for metadata toggle button
            let isMetadataPanelVisible = false;
            let lastDisplayMode = 'all'; // 'all' or 'mod-specific'
            let lastFilterValue = 'all';
            
            document.getElementById('metadata-toggle-btn').addEventListener('click', function() {
                const panel = document.getElementById('metadata-panel');
                if (panel.style.display === 'none' || !isMetadataPanelVisible) {
                    panel.style.display = 'block';
                    isMetadataPanelVisible = true;
                    // Load appropriate metadata display
                    const filterValue = document.getElementById('metadata-filter-select').value;
                    if (selectedModId) {
                        document.getElementById('metadata-input-section').style.display = 'block';
                        document.getElementById('metadata-title').textContent = `Assigned Metadata for Mod ${selectedModId}`;
                        loadAssignedMetadata(selectedModId, filterValue);
                        lastDisplayMode = 'mod-specific';
                        lastFilterValue = filterValue;
                    } else {
                        document.getElementById('metadata-input-section').style.display = 'none';
                        document.getElementById('metadata-title').textContent = 'All Metadata Pairs';
                        loadAllMetadata(filterValue);
                        lastDisplayMode = 'all';
                        lastFilterValue = filterValue;
                    }
                } else {
                    panel.style.display = 'none';
                    isMetadataPanelVisible = false;
                }
            });

            // Add metadata functionality - local operation
            document.getElementById('add-metadata-btn').addEventListener('click', function() {
                const type = document.getElementById('metadata-type-select').value;
                const value = document.getElementById('metadata-value-input').value.trim();
                
                if (!selectedModId) {
                    alert('Please select a mod first');
                    return;
                }
                
                if (!type) {
                    alert('Please select a metadata type');
                    return;
                }
                
                if (!value) {
                    alert('Please enter a metadata value');
                    return;
                }
                
                // Call Python function to add metadata
                pywebview.api.add_mod_metadata(selectedModId, type, value).then(function(result) {
                    console.log('Metadata added for mod ' + selectedModId + ': ' + type + ' -> ' + value);
                    // Refresh the metadata display
                    if (selectedModId) {
                        loadAssignedMetadata(selectedModId);
                    } else {
                        loadAllMetadata();
                    }
                }).catch(function(error) {
                    console.error('Error adding metadata:', error);
                });
            });

            // Filter functionality
            document.getElementById('metadata-filter-select').addEventListener('change', function() {
                const filterValue = this.value;
                if (selectedModId) {
                    loadAssignedMetadata(selectedModId, filterValue);
                } else {
                    loadAllMetadata(filterValue);
                }
            });

            // Delete mode checkbox functionality
            document.getElementById('delete-mode-checkbox').addEventListener('change', function() {
                const deleteMode = this.checked;
                const deleteBtn = document.getElementById('delete-selected-btn');
                const filterSelect = document.getElementById('metadata-filter-select');
                const metadataContent = document.getElementById('metadata-content');
                
                if (deleteMode) {
                    deleteBtn.style.display = 'inline-block';
                    // Update content to show checkboxes
                    updateDeleteModeContent();
                } else {
                    deleteBtn.style.display = 'none';
                    // Reload content without checkboxes
                    const filterValue = filterSelect.value;
                    if (selectedModId) {
                        loadAssignedMetadata(selectedModId, filterValue);
                    } else {
                        loadAllMetadata(filterValue);
                    }
                }
            });

            // Delete selected button functionality
            document.getElementById('delete-selected-btn').addEventListener('click', function() {
                if (confirm('Are you sure you want to delete the selected metadata items?')) {
                    const checkboxes = document.querySelectorAll('#metadata-content input[type="checkbox"]:checked');
                    const metadataIds = [];
                    
                    checkboxes.forEach(checkbox => {
                        // Get the metadata ID from the checkbox's dataset
                        const metadataId = checkbox.dataset.id;
                        if (metadataId) {
                            metadataIds.push(metadataId);
                        }
                    });
                    
                    // Delete all selected items
                    deleteSelectedMetadata(metadataIds);
                }
            });

            function updateDeleteModeContent() {
                const filterSelect = document.getElementById('metadata-filter-select');
                const filterValue = filterSelect.value;
                const contentDiv = document.getElementById('metadata-content');
                let currentContent = contentDiv.innerHTML;
                
                // If we're in delete mode, we need to add checkboxes to each metadata item
                if (currentContent && !currentContent.includes('type="checkbox"')) {
                    // Simple approach: re-load the content with checkboxes
                    if (selectedModId) {
                        loadAssignedMetadata(selectedModId, filterValue, true);
                    } else {
                        loadAllMetadata(filterValue, true);
                    }
                }
            }

            function loadAssignedMetadata(modId, filterType = 'all', deleteMode = false) {
                console.log('Loading metadata for mod:', modId, 'filter:', filterType);
                // Show loading indicator
                let content = '<i>Loading metadata...</i>';
                document.getElementById('metadata-content').innerHTML = content;
                document.getElementById('metadata-content').style.height = 'auto';
                
                // Call Python function to get metadata for specific mod
                pywebview.api.get_mod_metadata(modId, filterType).then(function(metadata) {
                    if (metadata && metadata.error) {
                        document.getElementById('metadata-content').innerHTML = '<i>Error loading metadata</i>';
                        return;
                    }
                    
                    let content = '';
                    if (metadata && metadata.length > 0) {
                        metadata.forEach(function(item) {
                            if (deleteMode) {
                                content += '<div style="margin-bottom: 0.5rem;"><input type="checkbox" id="metadata-' + item.id + '" data-id="' + item.id + '"> <label for="metadata-' + item.id + '">' + item.metadata + '</label></div>';
                            } else {
                                content += '<div style="margin-bottom: 0.5rem;">' + item.metadata + '</div>';
                            }
                        });
                    } else {
                        content = '<i>No metadata available</i>';
                    }
                    document.getElementById('metadata-content').innerHTML = content;
                    // Auto-resize the content area
                    document.getElementById('metadata-content').style.height = 'auto';
                }).catch(function(error) {
                    console.error('Error loading assigned metadata:', error);
                    document.getElementById('metadata-content').innerHTML = '<i>Error loading metadata</i>';
                    // Auto-resize the content area
                    document.getElementById('metadata-content').style.height = 'auto';
                });
            }

            function loadAllMetadata(filterType = 'all', deleteMode = false) {
                console.log('Loading all metadata, filter:', filterType);
                // Show loading indicator
                let content = '<i>Loading all metadata...</i>';
                document.getElementById('metadata-content').innerHTML = content;
                document.getElementById('metadata-content').style.height = 'auto';
                
                // Call Python function to get all metadata
                pywebview.api.get_all_metadata(filterType).then(function(metadata) {
                    if (metadata && metadata.error) {
                        document.getElementById('metadata-content').innerHTML = '<i>Error loading metadata</i>';
                        return;
                    }
                    
                    let content = '';
                    if (metadata && metadata.length > 0) {
                        metadata.forEach(function(item) {
                            if (deleteMode) {
                                content += '<div style="margin-bottom: 0.5rem;"><input type="checkbox" id="metadata-' + item.id + '" data-id="' + item.id + '"> <label for="metadata-' + item.id + '">' + item.metadata + '</label></div>';
                            } else {
                                content += '<div style="margin-bottom: 0.5rem;">' + item.metadata + '</div>';
                            }
                        });
                    } else {
                        content = '<i>No metadata available</i>';
                    }
                    document.getElementById('metadata-content').innerHTML = content;
                    // Auto-resize the content area
                    document.getElementById('metadata-content').style.height = 'auto';
                }).catch(function(error) {
                    console.error('Error loading all metadata:', error);
                    document.getElementById('metadata-content').innerHTML = '<i>Error loading metadata</i>';
                    // Auto-resize the content area
                    document.getElementById('metadata-content').style.height = 'auto';
                });
            }

            function deleteSelectedMetadata(metadataIds) {
                // Delete each selected metadata item
                const deletePromises = metadataIds.map(id => {
                    return pywebview.api.delete_metadata(id);
                });
                
                Promise.all(deletePromises).then(results => {
                    // Reload the content after deletion
                    if (selectedModId) {
                        loadAssignedMetadata(selectedModId);
                    } else {
                        loadAllMetadata();
                    }
                    alert('Selected metadata items deleted successfully!');
                }).catch(error => {
                    console.error('Error deleting metadata:', error);
                    alert('Error deleting metadata items');
                });
            }

            // Initialize panel to be hidden initially
            document.getElementById('metadata-panel').style.display = 'none';

            // Load metadata display when page loads (but wait for pywebview ready)
            // We'll load it in the pywebviewready event

            render();
        </script>
    </body>
    </html>
    """

    # Inject data safely via string replacement
    html = html_template.replace("MODS_DATA", mods_json).replace("SORT_CONFIG", sort_json)

    # Create Database API instance for PyWebView
    db_api = DatabaseAPI()
    
    # Create window with database API exposed to JavaScript
    window = webview.create_window('Insurgency:Sandstorm MOD.IO Manager', html=html, width=1000, height=700, js_api=db_api)
    webview.start()

if __name__ == "__main__":
    import sys
    
    # Check if reimport command is used
    if len(sys.argv) > 1 and sys.argv[1] == "reimport":
        print("Reimporting data from JSON to database...")
        # This will merge JSON with existing database data
        merged_data = merge_json_with_xml()
        print(f"Reimport completed. {len(merged_data)} mods processed.")
    else:
        start_manager()
    sys.exit()