import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import re

# Configure the page
st.set_page_config(
    page_title="Daily Geological Report Analyzer",
    page_icon="⛰️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e86ab;
        border-bottom: 2px solid #2e86ab;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .well-info-card {
        background-color: #f0f8ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .progress-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
    .formation-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ffeaa7;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def extract_well_info(df):
    """Extract well information from the first sheet"""
    well_info = {}
    
    # Find concession
    concession_cells = df[df.apply(lambda row: row.astype(str).str.contains('Concession', case=False).any(), axis=1)]
    if not concession_cells.empty:
        for idx, row in concession_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Concession' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['concession'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find well name
    well_cells = df[df.apply(lambda row: row.astype(str).str.contains('Well', case=False).any(), axis=1)]
    if not well_cells.empty:
        for idx, row in well_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Well' in str(cell) and ':-' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['well'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find date
    date_cells = df[df.apply(lambda row: row.astype(str).str.contains('Date', case=False).any(), axis=1)]
    if not date_cells.empty:
        for idx, row in date_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Date' in str(cell) and ':-' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['date'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find report number
    report_cells = df[df.apply(lambda row: row.astype(str).str.contains('Report No', case=False).any(), axis=1)]
    if not report_cells.empty:
        for idx, row in report_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Report No' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['report_no'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find RKB
    rkb_cells = df[df.apply(lambda row: row.astype(str).str.contains('RKB', case=False).any(), axis=1)]
    if not rkb_cells.empty:
        for idx, row in rkb_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'RKB' in str(cell) and ':-' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['rkb'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find spud date
    spud_cells = df[df.apply(lambda row: row.astype(str).str.contains('Spud Date', case=False).any(), axis=1)]
    if not spud_cells.empty:
        for idx, row in spud_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Spud Date' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['spud_date'] = str(row.iloc[col_idx + 1])
                    break
    
    # Find geologist
    geo_cells = df[df.apply(lambda row: row.astype(str).str.contains('Geologist', case=False).any(), axis=1)]
    if not geo_cells.empty:
        for idx, row in geo_cells.iterrows():
            for col_idx, cell in enumerate(row):
                if 'Geologist' in str(cell):
                    if col_idx + 1 < len(row):
                        well_info['geologist'] = str(row.iloc[col_idx + 1])
                    break
    else:
        # Try to find from the bottom of the sheet
        for idx in range(len(df)-1, max(0, len(df)-10), -1):
            row = df.iloc[idx]
            for cell in row:
                if 'Youssef' in str(cell) or 'Mahmoud' in str(cell) or 'Soliman' in str(cell):
                    well_info['geologist'] = str(cell)
                    break
    
    return well_info

@st.cache_data
def extract_depths(df):
    """Extract depth information"""
    depths = {}
    
    # Look for depth patterns
    for idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            cell_str = str(cell)
            if '24:00 Hrs' in cell_str and col_idx + 1 < len(row):
                try:
                    depths['depth_24hr'] = float(row.iloc[col_idx + 1])
                except:
                    pass
            elif '00:00 Hrs' in cell_str and col_idx + 1 < len(row):
                try:
                    depths['depth_00hr'] = float(row.iloc[col_idx + 1])
                except:
                    pass
            elif '06:00 Hrs' in cell_str and col_idx + 1 < len(row):
                try:
                    depths['depth_06hr'] = float(row.iloc[col_idx + 1])
                except:
                    pass
    
    # Calculate progress
    if 'depth_24hr' in depths and 'depth_00hr' in depths:
        depths['progress_24hr'] = depths['depth_00hr'] - depths['depth_24hr']
    
    if 'depth_00hr' in depths and 'depth_06hr' in depths:
        depths['progress_6hr'] = depths['depth_06hr'] - depths['depth_00hr']
    
    return depths

@st.cache_data
def extract_formation_tops(df):
    """Extract formation tops data"""
    formations = []
    
    # Look for the formation table header
    header_found = False
    for idx, row in df.iterrows():
        row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
        
        if 'Formation Name' in row_str and 'Prognosed' in row_str and 'Actual Drilled' in row_str:
            header_found = True
            header_row = idx
            continue
        
        if header_found and idx > header_row:
            # Check if this row contains formation data
            formation_data = {}
            
            # Get formation name (usually in column C)
            if len(row) > 2 and pd.notna(row.iloc[2]) and row.iloc[2] not in ['', ' ', 'DABAA', 'APOLLONIA', 'KHOMAN', 'ABU ROASH', 'BAHARIYA', 'KHARITA', 'T.D.']:
                formation_data['name'] = str(row.iloc[2])
                
                # Try to get prognosed MD (usually around column H)
                if len(row) > 7 and pd.notna(row.iloc[7]) and str(row.iloc[7]).replace('.', '').isdigit():
                    try:
                        formation_data['prognosed_md'] = float(row.iloc[7])
                    except:
                        pass
                
                # Try to get actual MD (usually around column J)
                if len(row) > 9 and pd.notna(row.iloc[9]) and str(row.iloc[9]).replace('.', '').isdigit():
                    try:
                        formation_data['actual_md'] = float(row.iloc[9])
                    except:
                        pass
                
                if formation_data:
                    formations.append(formation_data)
    
    return formations

@st.cache_data
def extract_gas_readings(df):
    """Extract gas reading summary"""
    gas_data = {}
    
    # Look for gas reading sections
    current_formation = None
    for idx, row in df.iterrows():
        for cell in row:
            cell_str = str(cell)
            
            # Look for formation names in gas sections
            if 'Max. Gas Reading at:' in cell_str:
                # Next cell should contain formation name
                cell_idx = row.tolist().index(cell)
                if cell_idx + 1 < len(row) and pd.notna(row.iloc[cell_idx + 1]):
                    current_formation = str(row.iloc[cell_idx + 1])
                    gas_data[current_formation] = {}
            
            # Look for TG values
            elif 'T.G' in cell_str and current_formation:
                # Look in subsequent rows for values
                for next_idx in range(idx + 1, min(idx + 5, len(df))):
                    next_row = df.iloc[next_idx]
                    if len(next_row) > 3 and pd.notna(next_row.iloc[3]) and str(next_row.iloc[3]).replace('.', '').isdigit():
                        try:
                            gas_data[current_formation]['TG'] = float(next_row.iloc[3])
                            break
                        except:
                            pass
    
    return gas_data

@st.cache_data
def extract_lithological_description(df):
    """Extract lithological description from second sheet"""
    descriptions = []
    
    current_depth = None
    current_lithology = None
    current_description = []
    
    for idx, row in df.iterrows():
        row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
        
        # Look for depth sections
        if 'Depth:' in row_str:
            # Save previous description if exists
            if current_depth and current_lithology and current_description:
                descriptions.append({
                    'depth': current_depth,
                    'lithology': current_lithology,
                    'description': ' '.join(current_description)
                })
            
            # Reset for new section
            current_description = []
            
            # Extract depth range
            depth_match = re.search(r'From.*?(\d+).*?To.*?(\d+)', row_str)
            if depth_match:
                current_depth = f"{depth_match.group(1)} - {depth_match.group(2)}"
        
        # Look for lithology type
        elif 'Lithology:' in row_str:
            lithology_match = re.search(r'Lithology:\s*\*\s*(.*?)$', row_str)
            if lithology_match:
                current_lithology = lithology_match.group(1).strip()
        
        # Collect description text (skip empty rows and headers)
        elif row_str.strip() and not any(keyword in row_str for keyword in ['North Bahariya', 'Well', 'Date', 'Lithological Description']):
            current_description.append(row_str.strip())
    
    # Add the last description
    if current_depth and current_lithology and current_description:
        descriptions.append({
            'depth': current_depth,
            'lithology': current_lithology,
            'description': ' '.join(current_description)
        })
    
    return descriptions

@st.cache_data
def extract_detailed_gas_readings(df):
    """Extract detailed gas readings from third sheet"""
    gas_readings = []
    
    # Find the header row
    header_found = False
    for idx, row in df.iterrows():
        row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
        
        if 'DEPTH' in row_str and 'TG' in row_str and 'C1' in row_str:
            header_found = True
            header_row = idx
            continue
        
        if header_found and idx > header_row:
            # Check if this is a data row (has depth number)
            if len(row) > 0 and pd.notna(row.iloc[0]) and str(row.iloc[0]).replace('.', '').isdigit():
                try:
                    depth = float(row.iloc[0])
                    reading = {'DEPTH': depth}
                    
                    # Extract gas readings (TG, C1, C2, C3, C4I, C4N, C5)
                    if len(row) > 7: reading['TG'] = float(row.iloc[7]) if pd.notna(row.iloc[7]) and str(row.iloc[7]).replace('.', '').isdigit() else 0
                    if len(row) > 8: reading['C1'] = float(row.iloc[8]) if pd.notna(row.iloc[8]) and str(row.iloc[8]).replace('.', '').isdigit() else 0
                    if len(row) > 9: reading['C2'] = float(row.iloc[9]) if pd.notna(row.iloc[9]) and str(row.iloc[9]).replace('.', '').isdigit() else 0
                    if len(row) > 10: reading['C3'] = float(row.iloc[10]) if pd.notna(row.iloc[10]) and str(row.iloc[10]).replace('.', '').isdigit() else 0
                    if len(row) > 11: reading['C4I'] = float(row.iloc[11]) if pd.notna(row.iloc[11]) and str(row.iloc[11]).replace('.', '').isdigit() else 0
                    if len(row) > 12: reading['C4N'] = float(row.iloc[12]) if pd.notna(row.iloc[12]) and str(row.iloc[12]).replace('.', '').isdigit() else 0
                    if len(row) > 13: reading['C5'] = float(row.iloc[13]) if pd.notna(row.iloc[13]) and str(row.iloc[13]).replace('.', '').isdigit() else 0
                    
                    gas_readings.append(reading)
                except:
                    continue
    
    return gas_readings

def main():
    st.markdown('<h1 class="main-header">Daily Geological Report Analyzer</h1>', unsafe_allow_html=True)
    
    # File upload
    uploaded_file = st.file_uploader("Upload Daily Geological Report (Excel file)", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            # Read all sheets
            daily_report_df = pd.read_excel(uploaded_file, sheet_name='Daily Geological Report', header=None)
            litho_desc_df = pd.read_excel(uploaded_file, sheet_name='Lithological Description', header=None)
            detailed_gas_df = pd.read_excel(uploaded_file, sheet_name='Lithology %, ROP & Gas Reading', header=None)
            
            # Extract data from all sheets
            well_info = extract_well_info(daily_report_df)
            depths = extract_depths(daily_report_df)
            formations = extract_formation_tops(daily_report_df)
            gas_summary = extract_gas_readings(daily_report_df)
            litho_descriptions = extract_lithological_description(litho_desc_df)
            detailed_gas = extract_detailed_gas_readings(detailed_gas_df)
            
            # Display results
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown('<div class="section-header">🏢 Well Information</div>', unsafe_allow_html=True)
                
                well_info_card = f"""
                <div class="well-info-card">
                    <strong>Concession:</strong> {well_info.get('concession', 'N/A')}<br>
                    <strong>Well:</strong> {well_info.get('well', 'N/A')}<br>
                    <strong>Date:</strong> {well_info.get('date', 'N/A')}<br>
                    <strong>Report No.:</strong> {well_info.get('report_no', 'N/A')}<br>
                    <strong>RKB:</strong> {well_info.get('rkb', 'N/A')} ft<br>
                    <strong>Spud Date:</strong> {well_info.get('spud_date', 'N/A')}<br>
                    <strong>Geologist:</strong> {well_info.get('geologist', 'N/A')}
                </div>
                """
                st.markdown(well_info_card, unsafe_allow_html=True)
                
                st.markdown('<div class="section-header">📊 Drilling Progress</div>', unsafe_allow_html=True)
                
                progress_card = f"""
                <div class="progress-card">
                    <strong>24:00 Hrs Depth:</strong> {depths.get('depth_24hr', 'N/A')} ft<br>
                    <strong>00:00 Hrs Depth:</strong> {depths.get('depth_00hr', 'N/A')} ft<br>
                    <strong>06:00 Hrs Depth:</strong> {depths.get('depth_06hr', 'N/A')} ft<br>
                    <strong>Progress (Last 24H):</strong> {depths.get('progress_24hr', 'N/A')} ft<br>
                    <strong>Progress (Last 6H):</strong> {depths.get('progress_6hr', 'N/A')} ft
                </div>
                """
                st.markdown(progress_card, unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="section-header">⛰️ Formation Tops</div>', unsafe_allow_html=True)
                
                if formations:
                    formation_data = []
                    for formation in formations:
                        formation_data.append([
                            formation.get('name', 'N/A'),
                            formation.get('prognosed_md', 'N/A'),
                            formation.get('actual_md', 'N/A')
                        ])
                    
                    formation_df = pd.DataFrame(formation_data, columns=['Formation', 'Prognosed MD (ft)', 'Actual MD (ft)'])
                    st.dataframe(formation_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No formation tops data found in the report.")
                
                st.markdown('<div class="section-header">🔥 Gas Reading Summary</div>', unsafe_allow_html=True)
                
                if gas_summary:
                    gas_data = []
                    for formation, readings in gas_summary.items():
                        gas_data.append([
                            formation,
                            readings.get('TG', 'N/A')
                        ])
                    
                    gas_df = pd.DataFrame(gas_data, columns=['Formation', 'Max TG (PPM)'])
                    st.dataframe(gas_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No gas reading summary found in the report.")
            
            # Lithological Descriptions
            st.markdown('<div class="section-header">🪨 Lithological Descriptions</div>', unsafe_allow_html=True)
            
            if litho_descriptions:
                for desc in litho_descriptions:
                    desc_card = f"""
                    <div class="formation-card">
                        <strong>Depth:</strong> {desc['depth']} ft<br>
                        <strong>Lithology:</strong> {desc['lithology']}<br>
                        <strong>Description:</strong> {desc['description'][:300]}...
                    </div>
                    """
                    st.markdown(desc_card, unsafe_allow_html=True)
            else:
                st.info("No lithological descriptions found in the report.")
            
            # Detailed Gas Readings Chart
            if detailed_gas:
                st.markdown('<div class="section-header">📈 Detailed Gas Readings</div>', unsafe_allow_html=True)
                
                gas_df = pd.DataFrame(detailed_gas)
                if not gas_df.empty:
                    # Show data table
                    st.dataframe(gas_df, use_container_width=True, hide_index=True)
                    
                    # Create chart
                    chart_data = gas_df.set_index('DEPTH')[['TG', 'C1', 'C2', 'C3']]
                    st.line_chart(chart_data)
            
        except Exception as e:
            st.error(f"Error processing the file: {str(e)}")
            st.info("Please make sure the Excel file has the correct structure with three sheets: 'Daily Geological Report', 'Lithological Description', and 'Lithology %, ROP & Gas Reading'")
    
    else:
        st.info("👆 Please upload a Daily Geological Report Excel file to get started.")
        
        # Show sample structure
        st.markdown("""
        ### Expected File Structure:
        
        The Excel file should contain 3 sheets:
        
        1. **Daily Geological Report** - Contains well information, drilling progress, formation tops, and gas summary
        2. **Lithological Description** - Contains detailed lithological descriptions
        3. **Lithology %, ROP & Gas Reading** - Contains detailed gas readings (TG, C1, C2, C3, C4I, C4N, C5)
        
        ### The app will extract:
        - 🏢 Well information (Concession, Date, Report No., RKB, Spud Date, Geologist)
        - 📊 Drilling progress and depths
        - ⛰️ Formation tops (actual vs prognosis)
        - 🔥 Gas reading summary
        - 🪨 Lithological descriptions
        - 📈 Detailed gas readings with charts
        """)

if __name__ == "__main__":
    main()