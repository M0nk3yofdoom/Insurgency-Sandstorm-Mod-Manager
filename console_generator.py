import sqlite3
import webview
import os
import time

# 1. PORTABILITY: Use the directory of the script itself
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mods.db")

class DatabaseAPI:
    """Database API for PyWebView to communicate with SQLite database."""
    
    def __init__(self):
        self.db_path = DB_PATH
        
    def get_all_mods(self):
        """Get all mods from database and categorize them by type, including relationship data."""
        try:
            print(f"Attempting to connect to database at: {self.db_path}")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create a dictionary to store categorized mods
            categorized_mods = {
                'Map': [],
                'Scenario': [],
                'Mutator': [],
                'MapScenarioRelationships': {}
            }
            
            # First, get all unique mod IDs and their associated maps and scenarios with full details
            cursor.execute("""
                SELECT m.id, mm.mod_type, mm.mod_value, mm.id as metadata_id
                FROM mods m 
                JOIN mod_metadata mm ON m.id = mm.mod_id
                WHERE mm.mod_type IN ('Map', 'Scenario')
                ORDER BY m.id, mm.mod_type
            """)
            
            # Group by mod_id to understand relationships - create direct ID mapping
            mod_relationships = {}
            
            for mod_row in cursor.fetchall():
                mod_id = mod_row[0]  # This is the mod_id from the mods table
                type_name = mod_row[1]  # This is the mod_type
                mod_name = mod_row[2]  # This is the mod_value
                metadata_id = mod_row[3]  # This is the metadata ID
                
                if mod_id not in mod_relationships:
                    mod_relationships[mod_id] = {'Map': [], 'Scenario': []}
                
                if type_name == 'Map':
                    mod_relationships[mod_id]['Map'].append(mod_name)
                elif type_name == 'Scenario':
                    mod_relationships[mod_id]['Scenario'].append(mod_name)
            
            # Store relationships for use in dropdown filtering
            categorized_mods['MapScenarioRelationships'] = mod_relationships
            
            # Get all unique maps and scenarios for dropdowns - use mod_metadata.id for unique identification
            cursor.execute("""
                SELECT DISTINCT m.id, mm.mod_type, mm.mod_value, mm.id as metadata_id
                FROM mods m 
                JOIN mod_metadata mm ON m.id = mm.mod_id
                WHERE mm.mod_type IN ('Map', 'Scenario', 'Mutator')
                ORDER BY mm.id
            """)
            all_mods = cursor.fetchall()
            
            print(f"Retrieved {len(all_mods)} mod metadata entries")
            
            # Categorize mods based on their type
            for mod_row in all_mods:
                mod_id = mod_row[0]  # This is the actual mod ID from mods table (for maps/scenarios)
                type_name = mod_row[1]  # This is the mod type
                mod_name = mod_row[2]  # This is the mod value
                metadata_id = mod_row[3]  # This is the metadata ID
                
                # Categorize each mod based on its type
                if type_name == 'Map':
                    categorized_mods['Map'].append((mod_id, mod_name))
                elif type_name == 'Scenario':
                    categorized_mods['Scenario'].append((mod_id, mod_name))
                elif type_name == 'Mutator':
                    # For mutators, we want to keep them ordered by metadata_id (which is mm.id)
                    # For the UI, we'll use the metadata_id as the identifier for the checkbox
                    # The mod_id (first element) is the unique identifier for the checkbox value
                    categorized_mods['Mutator'].append((metadata_id, mod_name))
            
            # Ensure mutators are sorted by their metadata_id (which is mm.id)
            # Since we ordered by mm.id in the SQL query, they should already be in correct order
            # But for extra safety, we can sort them explicitly
            categorized_mods['Mutator'].sort(key=lambda x: x[0])  # Sort by metadata_id (first element)
            
            conn.close()
            
            print(f"Final categorized data: Maps={len(categorized_mods['Map'])}, Scenarios={len(categorized_mods['Scenario'])}, Mutators={len(categorized_mods['Mutator'])}")
            return categorized_mods
        except Exception as e:
            print(f"Error fetching mods: {e}")
            import traceback
            traceback.print_exc()
            return {'Map': [], 'Scenario': [], 'Mutator': [], 'MapScenarioRelationships': {}}

# Create an API wrapper that provides the proper interface
class API:
    def __init__(self):
        self.db_api = DatabaseAPI()
        
    def get_all_mods(self):
        try:
            result = self.db_api.get_all_mods()
            print("API get_all_mods() called, returning:", result)
            return result
        except Exception as e:
            print("ERROR in get_all_mods:", e)
            import traceback
            traceback.print_exc()
            return {'Map': [], 'Scenario': [], 'Mutator': [], 'MapScenarioRelationships': {}}
        
    def generate_command(self, selected_maps, selected_scenarios, selected_mutators, lighting):
        try:
            # Get the latest data from database
            all_mods_data = self.db_api.get_all_mods()
            result = generate_command(selected_maps, selected_scenarios, selected_mutators, lighting, all_mods_data)
            print("API generate_command() called, returning:", result)
            return result
        except Exception as e:
            print("ERROR in generate_command:", e)
            import traceback
            traceback.print_exc()
            return "Error generating command"

# Create the API instance for PyWebView
api = API()

# Generate console command
def generate_command(selected_maps, selected_scenarios, selected_mutators, lighting, all_mods_data):
    # Build the travel command in the specified format
    command_parts = []
    
    # Add travel command
    command_parts.append("travel")
    
    # Add map (only one allowed) - using value instead of ID
    if selected_maps and all_mods_data:
        # Get the actual mod value from all_mods_data
        map_id = selected_maps[0]
        map_value = None
        for mod_id, mod_name in all_mods_data.get('Map', []):
            if str(mod_id) == str(map_id):
                map_value = mod_name
                break
        if map_value:
            command_parts.append(str(map_value))
        else:
            # Fallback to ID if value not found
            command_parts.append(str(map_id))
    
    # Add scenario (only one allowed)
    if selected_scenarios and all_mods_data:
        # Get the actual mod value from all_mods_data
        scenario_id = selected_scenarios[0]
        scenario_value = None
        for mod_id, mod_name in all_mods_data.get('Scenario', []):
            if str(mod_id) == str(scenario_id):
                scenario_value = mod_name
                break
        if scenario_value:
            command_parts.append(f"?Scenario={scenario_value}")
        else:
            # Fallback to ID if value not found
            command_parts.append(f"?Scenario={scenario_id}")
    
    # Add lighting if selected (not '-')
    if lighting and lighting != '-':
        command_parts.append(f"?lighting={lighting}")
    
    # Add mutators if any exist based on their unique ID not their mod_ID(optional)
    if selected_mutators and all_mods_data:
        # Get the actual mod values from all_mods_data
        mutator_values = []
        for mutator_id in selected_mutators:
            for id, mod_name in all_mods_data.get('Mutator', []):
                if str(id) == str(mutator_id):
                    mutator_values.append(mod_name)
                    break
        if mutator_values:
            mutators_str = ",".join(mutator_values)
            command_parts.append(f"?Mutators={mutators_str}")
        else:
            # Fallback to IDs if values not found
            mutators_str = ",".join(selected_mutators)
            command_parts.append(f"?Mutators={mutators_str}")
    
    # Join with spaces to get the final command
    command = " ".join(command_parts)
    # Ensure no spaces around the ? characters as requested
    command = command.replace(" ?Scenario=", "?Scenario=").replace(" ?lighting=", "?lighting=").replace(" ?Mutators=", "?Mutators=")
    return command

# HTML template for the application - simplified version
html_template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Console Command Generator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #171317;
            color: #DDBFA2;
        }
        .container {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            height: 70vh;
        }
        .column {
            flex: 1;
            border: 2px solid #6C4534;
            border-radius: 5px;
            padding: 10px;
            background-color: #171317;
            overflow-y: auto;
            max-height: 100%;
        }
        .column h2 {
            margin-top: 0;
            margin-bottom: 15px;
            text-align: center;
            color: #AB381C;
            border-bottom: 2px solid #6C4534;
            padding-bottom: 5px;
        }
        .checkbox-row {
            margin: 5px 0;
            padding: 5px;
            border-bottom: 1px solid #6C4534;
        }
        .checkbox-row:hover {
            background-color: #6C4534;
        }
        .command-container {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 20px;
        }
        .lighting-selector {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .lighting-selector label {
            margin: 0;
        }
        #commandInput {
            flex: 1;
            padding: 10px;
            border: 2px solid #6C4534;
            border-radius: 3px;
            background-color: #171317;
            color: #DDBFA2;
        }
        #copyButton {
            padding: 10px 20px;
            background-color: #AB381C;
            color: #DDBFA2;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        #copyButton:hover {
            background-color: #858F8B;
        }
        #lightingSelector {
            padding: 5px;
            background-color: #171317;
            color: #DDBFA2;
            border: 1px solid #6C4534;
            border-radius: 3px;
        }
        .checkbox-row input[type="checkbox"] {
            margin-right: 10px;
            accent-color: #5A6FA8;
        }
        h1 {
            color: #DDBFA2;
            text-align: center;
        }
        .layout-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .layout-row {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .mutators-column {
            display: flex;
            flex-direction: column;
        }
        .mutators-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .mutators-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        #clearMutatorsButton {
            padding: 5px 10px;
            background-color: #AB381C;
            color: #DDBFA2;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
        }
        #clearMutatorsButton:hover {
            background-color: #858F8B;
        }
        .dropdown {
            width: 100%;
            padding: 8px;
            background-color: #171317;
            color: #DDBFA2;
            border: 1px solid #6C4534;
            border-radius: 3px;
            margin-bottom: 5px;
        }
        .status-message {
            color: #DDBFA2;
            font-weight: bold;
            padding: 10px;
            background-color: #2a2525;
            border-radius: 3px;
            margin: 5px 0;
        }
        .error-message {
            color: red;
            font-weight: bold;
            padding: 10px;
            background-color: #2a2525;
            border-radius: 3px;
            margin: 5px 0;
        }
        /* Highlight for selected dropdown */
        .highlight-map {
            border: 2px solid #5A6FA8 !important;
            background-color: #1d1a22 !important;
        }
        .highlight-scenario {
            border: 2px solid #5A6FA8 !important;
            background-color: #1d1a22 !important;
        }
    </style>
</head>
<body>
    <h1>Console Command Generator</h1>
    
    <div class="layout-container">
        <div class="layout-row">
            <div class="column" style="flex: 1;">
                <h2>Map</h2>
                <div id="mapsContainer" class="status-message">Loading maps...</div>
            </div>
            <div class="column" style="flex: 0.1; display: flex; align-items: center; justify-content: center;">
                <button id="clearSelectionButton" style="padding: 10px 15px; background-color: #AB381C; color: #DDBFA2; border: none; border-radius: 3px; cursor: pointer; font-size: 14px;">Reset</button>
            </div>
            <div class="column" style="flex: 1;">
                <h2>Scenario</h2>
                <div id="scenariosContainer" class="status-message">Loading scenarios...</div>
            </div>
        </div>
        
        <div class="layout-row">
            <div class="column mutators-column" style="flex: 1;">
                <div class="mutators-header">
                    <h2>Mutators</h2>
                    <button id="clearMutatorsButton">Clear Checked</button>
                </div>
                <div id="mutatorsContainer" class="status-message">Loading mutators...</div>
            </div>
        </div>
        
        <div class="layout-row">
            <div class="lighting-selector">
                <label for="lightingSelector">Lighting:</label>
                <select id="lightingSelector">
                    <option value="-">-</option>
                    <option value="Day">Day</option>
                    <option value="Night">Night</option>
                </select>
            </div>
            <input type="text" id="commandInput" placeholder="Generated command will appear here">
            <button id="copyButton">Copy Command</button>
        </div>
    </div>

    <script>
        // Simple function to check if API is available
        function checkAPI() {
            try {
                if (typeof window.pywebview !== 'undefined' && window.pywebview.api) {
                    console.log('pywebview.api is available');
                    return true;
                } else {
                    console.log('pywebview.api is NOT available');
                    return false;
                }
            } catch (e) {
                console.log('Error checking API:', e);
                return false;
            }
        }
        
        // Improved API readiness check with retry mechanism
        function waitForAPI(maxRetries = 10, retryDelay = 100) {
            return new Promise((resolve) => {
                let attempts = 0;
                
                function check() {
                    attempts++;
                    if (checkAPI()) {
                        resolve();
                    } else if (attempts >= maxRetries) {
                        console.log('API not ready after ' + maxRetries + ' attempts, proceeding anyway');
                        // Proceed anyway to avoid blocking startup - this is critical for avoiding race conditions
                        resolve();
                    } else {
                        setTimeout(check, retryDelay);
                    }
                }
                
                check();
            });
        }
        
        let selectedMaps = [];
        let selectedScenarios = [];
        let selectedMutators = [];
        let allMods = {};
        let mapScenarioRelationships = {};
        let filtersApplied = false; // Flag to track if filters have been applied
        
        // Initialize the application
        function init() {
            console.log('Application initializing...');
            // Try to initialize API immediately but be resilient
            fetchMods();
            
            // Make sure we don't get stuck in loading state even if API doesn't work
            setTimeout(() => {
                try {
                    const mapsContainer = document.getElementById('mapsContainer');
                    const scenariosContainer = document.getElementById('scenariosContainer');
                    const mutatorsContainer = document.getElementById('mutatorsContainer');
                    
                    if (mapsContainer && mapsContainer.innerHTML.includes('Loading maps')) {
                        console.log('Maps still loading after timeout, showing empty state');
                        mapsContainer.innerHTML = '<div class="status-message">No maps available</div>';
                    }
                    if (scenariosContainer && scenariosContainer.innerHTML.includes('Loading scenarios')) {
                        console.log('Scenarios still loading after timeout, showing empty state');
                        scenariosContainer.innerHTML = '<div class="status-message">No scenarios available</div>';
                    }
                    if (mutatorsContainer && mutatorsContainer.innerHTML.includes('Loading mutators')) {
                        console.log('Mutators still loading after timeout, showing empty state');
                        mutatorsContainer.innerHTML = '<div class="status-message">No mutators available</div>';
                    }
                } catch (e) {
                    console.log('Error in timeout handler:', e);
                }
            }, 5000); // 5 second timeout
        }
        
        // Fetch mods from the backend
        function fetchMods() {
            console.log('Attempting to fetch mods from API...');
            // Make the API call with error handling
            if (window.pywebview && window.pywebview.api) {
                console.log('API is available, calling get_all_mods()');
                window.pywebview.api.get_all_mods().then(function(response) {
                    console.log('Received mods data:', response);
                    allMods = response;
                    mapScenarioRelationships = response.MapScenarioRelationships || {};
                    populateColumns(response);
                    updateCommand();
                }).catch(function(error) {
                    console.log('Failed to fetch mods:', error);
                    showError('Error: ' + error.message);
                });
            } else {
                console.log('API not available yet, will retry in 100ms');
                setTimeout(fetchMods, 100);
            }
        }
        
        // Show error message
        function showError(message) {
            console.log('Showing error:', message);
            document.getElementById('mapsContainer').innerHTML = '<div class="error-message">Error: ' + message + '</div>';
            document.getElementById('scenariosContainer').innerHTML = '<div class="error-message">Error: ' + message + '</div>';
            document.getElementById('mutatorsContainer').innerHTML = '<div class="error-message">Error: ' + message + '</div>';
        }
        
        // Populate the columns with mod data
        function populateColumns(mods) {
            console.log('Populating columns with data');
            
            try {
                // Maps
                const mapsContainer = document.getElementById('mapsContainer');
                if (mods.Map && mods.Map.length > 0) {
                    mapsContainer.innerHTML = '<select id="mapsDropdown" class="dropdown"><option value="">Select a Map</option>' + 
                        mods.Map.map(map => `<option value="${map[0]}">${map[1]}</option>`).join('') + 
                        '</select>';
                } else {
                    mapsContainer.innerHTML = '<div class="status-message">No maps available</div>';
                }
                
                // Scenarios
                const scenariosContainer = document.getElementById('scenariosContainer');
                if (mods.Scenario && mods.Scenario.length > 0) {
                    scenariosContainer.innerHTML = '<select id="scenariosDropdown" class="dropdown"><option value="">Select a Scenario</option>' + 
                        mods.Scenario.map(scenario => `<option value="${scenario[0]}">${scenario[1]}</option>`).join('') + 
                        '</select>';
                } else {
                    scenariosContainer.innerHTML = '<div class="status-message">No scenarios available</div>';
                }
                
                // Mutators
                const mutatorsContainer = document.getElementById('mutatorsContainer');
                if (mods.Mutator && mods.Mutator.length > 0) {
                    // Create a grid layout with 3 columns
                    const mutatorsHTML = mods.Mutator.map(mutator => {
                        const mutatorId = mutator[0];  // This is the ID from mods table
                        const mutatorValue = mutator[1];  // This is the mod_value
                        return `<div class="checkbox-row" style="margin:0;padding:5px;"><input type="checkbox" id="mutator-${mutatorId}" value="${mutatorId}"><label for="mutator-${mutatorId}">${mutatorValue}</label></div>`;
                    }).join('');
                    
                    mutatorsContainer.innerHTML = `<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">${mutatorsHTML}</div>`;
                } else {
                    mutatorsContainer.innerHTML = '<div class="status-message"><i>No mutators available</i></div>';
                }
                
                console.log('Columns populated successfully');
                
                // Setup event listeners
                setupEventListeners();
            } catch (e) {
                console.log('Error in populateColumns:', e);
                showError('Render Error: ' + e.message);
            }
        }
        
        // Setup event listeners for dropdowns and lighting selector
        function setupEventListeners() {
            console.log('Setting up event listeners');
            
            // Map dropdown
            const mapsDropdown = document.getElementById('mapsDropdown');
            if (mapsDropdown) {
                mapsDropdown.addEventListener('change', function(event) {
                    const selectedMapId = event.target.value;
                    selectedMaps = selectedMapId ? [selectedMapId] : [];
                    
                    // Clear any previous highlights
                    document.querySelectorAll('.column').forEach(col => {
                        col.classList.remove('highlight-map', 'highlight-scenario');
                    });
                    
                    // Highlight the map column when a map is selected
                    if (selectedMapId) {
                        const mapColumn = event.target.closest('.column');
                        if (mapColumn) {
                            mapColumn.classList.add('highlight-map');
                        }
                    }
                    
                    // When a map is selected, we need to filter scenarios
                    filterScenariosByMap(selectedMapId);
                    
                    updateCommand();
                    console.log('Map selected: ' + selectedMapId);
                });
            } else {
                console.log('WARNING: Maps dropdown not found');
            }
            
            // Scenario dropdown
            const scenariosDropdown = document.getElementById('scenariosDropdown');
            if (scenariosDropdown) {
                scenariosDropdown.addEventListener('change', function(event) {
                    const selectedScenarioId = event.target.value;
                    selectedScenarios = selectedScenarioId ? [selectedScenarioId] : [];
                    
                    // Clear any previous highlights
                    document.querySelectorAll('.column').forEach(col => {
                        col.classList.remove('highlight-map', 'highlight-scenario');
                    });
                    
                    // Highlight the scenario column when a scenario is selected
                    if (selectedScenarioId) {
                        const scenarioColumn = event.target.closest('.column');
                        if (scenarioColumn) {
                            scenarioColumn.classList.add('highlight-scenario');
                        }
                    }
                    
                    // When a scenario is selected, we need to filter maps
                    filterMapsByScenario(selectedScenarioId);
                    
                    updateCommand();
                    console.log('Scenario selected: ' + selectedScenarioId);
                });
            } else {
                console.log('WARNING: Scenarios dropdown not found');
            }
            
            // Mutators event listeners
            document.querySelectorAll('#mutatorsContainer input[type="checkbox"]').forEach(function(checkbox) {
                checkbox.addEventListener('change', function(event) {
                    const mutatorId = event.target.value;
                    const isChecked = event.target.checked;
                    
                    if (isChecked) {
                        selectedMutators.push(mutatorId);
                    } else {
                        selectedMutators = selectedMutators.filter(function(id) { return id !== mutatorId; });
                    }
                    
                    updateCommand();
                    console.log('Mutator ' + mutatorId + ' ' + (isChecked ? 'selected' : 'deselected'));
                });
            });
            
            // Lighting selector
            const lightingSelector = document.getElementById('lightingSelector');
            if (lightingSelector) {
                lightingSelector.addEventListener('change', updateCommand);
            }
            
            // Copy button
            const copyButton = document.getElementById('copyButton');
            if (copyButton) {
                copyButton.addEventListener('click', function() {
                    const command = document.getElementById('commandInput').value;
                    if (command) {
                        copyToClipboard(command);
                    } else {
                        showCopyFeedback('Nothing to copy');
                    }
                });
            }
            
            // Clear mutators button
            const clearMutatorsButton = document.getElementById('clearMutatorsButton');
            if (clearMutatorsButton) {
                clearMutatorsButton.addEventListener('click', function() {
                    document.querySelectorAll('#mutatorsContainer input[type="checkbox"]:checked').forEach(function(checkbox) {
                        checkbox.checked = false;
                    });
                    selectedMutators = [];
                    updateCommand();
                    console.log('Cleared mutators');
                });
            }
            
            // Clear selection button
            const clearSelectionButton = document.getElementById('clearSelectionButton');
            if (clearSelectionButton) {
                clearSelectionButton.addEventListener('click', function() {
                    // Reset both dropdowns to initial state
                    const mapsDropdown = document.getElementById('mapsDropdown');
                    const scenariosDropdown = document.getElementById('scenariosDropdown');
                    
                    if (mapsDropdown) {
                        mapsDropdown.selectedIndex = 0; // Reset to first option (placeholder)
                        selectedMaps = [];
                    }
                    
                    if (scenariosDropdown) {
                        scenariosDropdown.selectedIndex = 0; // Reset to first option (placeholder)
                        selectedScenarios = [];
                    }
                    
                    // Reset dropdowns to show all options
                    resetDropdowns();
                    
                    updateCommand();
                    console.log('Selection cleared');
                });
            }
        }
        
        // Filter scenarios based on selected map
        function filterScenariosByMap(selectedMapId) {
            console.log('filterScenariosByMap called with map ID:', selectedMapId);
            console.log('Current selected scenarios:', selectedScenarios);
            console.log('Current selected maps:', selectedMaps);
            console.log('mapScenarioRelationships:', mapScenarioRelationships);
            
            // Only filter scenarios if NO scenario is already selected AND no filters applied yet
            if (selectedScenarios.length > 0 || filtersApplied) {
                console.log('Skipping scenario filtering - scenario already selected or filters already applied');
                return;
            }
            
            const scenariosDropdown = document.getElementById('scenariosDropdown');
            if (!scenariosDropdown || !mapScenarioRelationships) {
                console.log('Skipping scenario filtering - missing elements');
                return;
            }
            
            // Mark that filters have been applied to prevent further filtering
            filtersApplied = true;
            
            // Reset the scenarios dropdown to default state (keep same structure)
            const options = scenariosDropdown.querySelectorAll('option');
            for (let i = options.length - 1; i > 0; i--) {
                options[i].remove();
            }
            
            // Add back the placeholder
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select a Scenario';
            scenariosDropdown.appendChild(placeholder);
            
            // If a map is selected, only show scenarios related to that map
            if (selectedMapId && mapScenarioRelationships[selectedMapId]) {
                const relatedScenarios = mapScenarioRelationships[selectedMapId].Scenario;
                console.log('Related scenarios for map ' + selectedMapId + ':', relatedScenarios);
                if (relatedScenarios && relatedScenarios.length > 0) {
                    // Find scenario IDs that match these names
                    if (allMods.Scenario && allMods.Scenario.length > 0) {
                        allMods.Scenario.forEach(function(scenario) {
                            if (relatedScenarios.includes(scenario[1])) {
                                const option = document.createElement('option');
                                option.value = scenario[0];
                                option.textContent = scenario[1];
                                scenariosDropdown.appendChild(option);
                                console.log('Added scenario option:', scenario[1]);
                            }
                        });
                    }
                }
            }
            console.log('Scenario filtering completed');
        }
        
        // Filter maps based on selected scenario
        function filterMapsByScenario(selectedScenarioId) {
            console.log('filterMapsByScenario called with scenario ID:', selectedScenarioId);
            console.log('Current selected scenarios:', selectedScenarios);
            console.log('Current selected maps:', selectedMaps);
            console.log('mapScenarioRelationships:', mapScenarioRelationships);
            
            // Only filter maps if NO map is already selected AND no filters applied yet
            if (selectedMaps.length > 0 || filtersApplied) {
                console.log('Skipping map filtering - map already selected or filters already applied');
                return;
            }
            
            const mapsDropdown = document.getElementById('mapsDropdown');
            if (!mapsDropdown || !mapScenarioRelationships) {
                console.log('Skipping map filtering - missing elements');
                return;
            }
            
            // Mark that filters have been applied to prevent further filtering
            filtersApplied = true;
            
            // Reset the maps dropdown to default state (keep same structure)
            const options = mapsDropdown.querySelectorAll('option');
            for (let i = options.length - 1; i > 0; i--) {
                options[i].remove();
            }
            
            // Add back the placeholder
            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select a Map';
            mapsDropdown.appendChild(placeholder);
            
            // If a scenario is selected, only show maps related to that scenario
            if (selectedScenarioId) {
                // Build a reverse mapping from scenario names to mod IDs
                const scenarioToModMap = {};
                
                // Build reverse mapping from scenario names to mod IDs
                for (const [modId, relationships] of Object.entries(mapScenarioRelationships)) {
                    if (relationships.Scenario && relationships.Scenario.length > 0) {
                        relationships.Scenario.forEach(function(scenarioName) {
                            if (!scenarioToModMap[scenarioName]) {
                                scenarioToModMap[scenarioName] = [];
                            }
                            scenarioToModMap[scenarioName].push(modId);
                        });
                    }
                }
                
                // Find which scenario name corresponds to the selected scenario ID
                let scenarioName = null;
                if (allMods.Scenario && allMods.Scenario.length > 0) {
                    const scenario = allMods.Scenario.find(s => s[0] === selectedScenarioId);
                    if (scenario) {
                        scenarioName = scenario[1];
                    }
                }
                
                console.log('Scenario name for ID ' + selectedScenarioId + ':', scenarioName);
                
                // Get the mod IDs that have this scenario name
                const relatedModIds = scenarioToModMap[scenarioName] || [];
                console.log('Related mod IDs for scenario "' + scenarioName + '":', relatedModIds);
                
                // Add back only maps that are related to this scenario
                if (relatedModIds.length > 0) {
                    // For each mod ID that has this scenario, find all maps associated with that mod ID
                    relatedModIds.forEach(function(modId) {
                        // If this mod ID has maps, add them to dropdown
                        if (mapScenarioRelationships[modId] && mapScenarioRelationships[modId].Map && mapScenarioRelationships[modId].Map.length > 0) {
                            // Add all maps related to this mod ID to dropdown
                            const relatedMaps = mapScenarioRelationships[modId].Map;
                            console.log('Adding maps related to mod ID ' + modId + ':', relatedMaps);
                            relatedMaps.forEach(function(mapName) {
                                if (allMods.Map && allMods.Map.length > 0) {
                                    const map = allMods.Map.find(m => m[1] === mapName);
                                    if (map) {
                                        const option = document.createElement('option');
                                        option.value = map[0];
                                        option.textContent = map[1];
                                        mapsDropdown.appendChild(option);
                                        console.log('Added map option:', map[1]);
                                    }
                                }
                            });
                        }
                    });
                }
            }
            console.log('Map filtering completed');
        }
        
        // Reset dropdowns to show all options
        function resetDropdowns() {
            // Reset filtersApplied flag to allow new filtering
            filtersApplied = false;
            
            // Reset maps dropdown to show all options
            const mapsDropdown = document.getElementById('mapsDropdown');
            if (mapsDropdown && allMods.Map) {
                // Clear all options except the first (placeholder)
                const options = mapsDropdown.querySelectorAll('option');
                for (let i = options.length - 1; i > 0; i--) {
                    options[i].remove();
                }
                
                // Add all maps back
                allMods.Map.forEach(function(map) {
                    const option = document.createElement('option');
                    option.value = map[0];
                    option.textContent = map[1];
                    mapsDropdown.appendChild(option);
                });
            }
            
            // Reset scenarios dropdown to show all options
            const scenariosDropdown = document.getElementById('scenariosDropdown');
            if (scenariosDropdown && allMods.Scenario) {
                // Clear all options except the first (placeholder)
                const options = scenariosDropdown.querySelectorAll('option');
                for (let i = options.length - 1; i > 0; i--) {
                    options[i].remove();
                }
                
                // Add all scenarios back
                allMods.Scenario.forEach(function(scenario) {
                    const option = document.createElement('option');
                    option.value = scenario[0];
                    option.textContent = scenario[1];
                    scenariosDropdown.appendChild(option);
                });
            }
        }
        
        // Update the command input field
        function updateCommand() {
            console.log('Updating command');
            const lighting = document.getElementById('lightingSelector').value;
            
            // If API is available, try to generate command
            if (window.pywebview && window.pywebview.api) {
                try {
                    window.pywebview.api.generate_command(selectedMaps, selectedScenarios, selectedMutators, lighting).then(function(command) {
                        document.getElementById('commandInput').value = command;
                        console.log('Command updated: ' + command);
                    }).catch(function(error) {
                        console.log('Failed to generate command: ' + error.message);
                        document.getElementById('commandInput').value = 'Error generating command';
                    });
                } catch (error) {
                    console.log('API call failed with exception: ' + error.message);
                    // Don't retry immediately - just show error
                    document.getElementById('commandInput').value = 'Error generating command';
                }
            } else {
                // If API not available, don't crash, just show placeholder
                console.log('API not available yet, showing placeholder');
                // Don't set value here to avoid overwriting user input
            }
        }
        
        // Copy to clipboard function - fallback for PyWebView environment
        function copyToClipboard(text) {
            // First try the modern clipboard API
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(function() {
                    console.log('Copied to clipboard: ' + text);
                    // Show success feedback to user
                    showCopyFeedback('Copied to clipboard!');
                }).catch(function(error) {
                    console.error('Failed to copy with modern API: ', error);
                    // Fallback to legacy method
                    fallbackCopyTextToClipboard(text);
                });
            } else {
                // Fallback for environments without clipboard API or insecure context
                fallbackCopyTextToClipboard(text);
            }
        }
        
        // Fallback method for copying to clipboard
        function fallbackCopyTextToClipboard(text) {
            const textArea = document.createElement("textarea");
            textArea.value = text;
            
            // Move textarea off-screen
            textArea.style.position = "fixed";
            textArea.style.left = "-999999px";
            textArea.style.top = "-999999px";
            
            document.body.appendChild(textArea);
            textArea.select();
            
            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    console.log('Copied to clipboard: ' + text);
                    showCopyFeedback('Copied to clipboard!');
                } else {
                    console.error('Failed to copy with fallback method');
                    showCopyFeedback('Failed to copy to clipboard');
                }
            } catch (err) {
                console.error('Fallback copy failed: ', err);
                showCopyFeedback('Failed to copy to clipboard');
            }
            
            document.body.removeChild(textArea);
        }
        
        // Show feedback to user
        function showCopyFeedback(message) {
            // Create a temporary feedback element
            const feedback = document.createElement('div');
            feedback.textContent = message;
            feedback.style.position = 'fixed';
            feedback.style.bottom = '20px';
            feedback.style.right = '20px';
            feedback.style.backgroundColor = '#AB381C';
            feedback.style.color = '#DDBFA2';
            feedback.style.padding = '10px';
            feedback.style.borderRadius = '3px';
            feedback.style.zIndex = '1000';
            feedback.style.opacity = '0';
            feedback.style.transition = 'opacity 0.3s';
            
            document.body.appendChild(feedback);
            
            // Fade in
            setTimeout(() => {
                feedback.style.opacity = '1';
            }, 10);
            
            // Remove after delay
            setTimeout(() => {
                feedback.style.opacity = '0';
                setTimeout(() => {
                    if (feedback.parentNode) {
                        feedback.parentNode.removeChild(feedback);
                    }
                }, 300);
            }, 2000);
        }
        
        // Initialize when page loads
        window.addEventListener('load', init);
        console.log('Page loaded event registered');
    </script>
</body>
</html>
'''

def start_console_generator():
    """Start the console generator webview application."""
    # Start the webview window
    print("Creating webview window...")
    try:
        window = webview.create_window('Console Command Generator', html=html_template, js_api=api, width=1200, height=800)
        print("Webview window created successfully")
    except Exception as e:
        print(f"Failed to create webview window: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    print("Starting webview...")
    try:
        # Ensure that webview.start() keeps the process alive by running in a loop
        # Also add some debugging to make sure it's not exiting immediately
        print("About to start webview event loop...")
        # Try a more traditional approach to ensure compatibility
        import sys
        if sys.platform.startswith('darwin'):  # macOS
            webview.start(debug=False, gui='cocoa')
        else:
            webview.start(debug=False)
        print("Webview started successfully")
    except Exception as e:
        print(f"Failed to start webview: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

def main():
    """Main entry point for the console generator."""
    print("Starting Console Command Generator...")
    
    # Test database connection with debugging
    try:
        print("Testing database connection...")
        test_mods = api.get_all_mods()
        print(f"Database connection successful. Found {len(test_mods['Map'])} maps, {len(test_mods['Scenario'])} scenarios, {len(test_mods['Mutator'])} mutators")
        print(f"Map data: {test_mods['Map']}")
        print(f"Scenario data: {test_mods['Scenario']}")
        print(f"Mutator data: {test_mods['Mutator']}")
    except Exception as e:
        print(f"Database connection failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Start the actual application
    start_console_generator()

if __name__ == "__main__":
    main()