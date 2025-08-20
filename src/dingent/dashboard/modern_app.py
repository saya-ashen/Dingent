import streamlit as st

# Enhanced Admin Dashboard App
st.set_page_config(
    page_title="Dingent Admin Dashboard", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS Styling for Modern Look
st.markdown("""
<style>
    /* Main container styling */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Header styling */
    .css-18e3th9 {
        padding-top: 0;
        padding-bottom: 1rem;
        background: white;
        border-bottom: 1px solid #e0e0e0;
    }
    
    /* Card-like containers */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        text-align: center;
        margin: 0.25rem;
    }
    
    .status-success {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-warning {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .status-error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .status-info {
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f8f9fa;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 8px;
        color: #495057;
        font-weight: 500;
        border: none;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Table styling */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 10px;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 8px;
        font-weight: 500;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Modern header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 300;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown("""
<div class="main-header">
    <h1>🤖 Dingent Admin Dashboard</h1>
    <p>Modern React-style Admin Interface for AI Agent Management</p>
</div>
""", unsafe_allow_html=True)

# Sample dashboard content for demonstration
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="metric-card">
        <h3 style="color: #667eea; margin: 0 0 0.5rem 0;">🤖 Active Assistants</h3>
        <h2 style="margin: 0; color: #2c3e50;">3 / 5</h2>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">Currently running</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card">
        <h3 style="color: #28a745; margin: 0 0 0.5rem 0;">🔌 Available Plugins</h3>
        <h2 style="margin: 0; color: #2c3e50;">12</h2>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">Ready to use</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <h3 style="color: #ffc107; margin: 0 0 0.5rem 0;">⚠️ Warnings</h3>
        <h2 style="margin: 0; color: #2c3e50;">2</h2>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">Need attention</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card">
        <h3 style="color: #dc3545; margin: 0 0 0.5rem 0;">❌ Errors</h3>
        <h2 style="margin: 0; color: #2c3e50;">0</h2>
        <p style="margin: 0.5rem 0 0 0; color: #6c757d;">All systems OK</p>
    </div>
    """, unsafe_allow_html=True)

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🤖 Assistants", "🔌 Plugins", "📋 Logs"])

with tab1:
    st.subheader("🎯 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Deploy New Assistant", use_container_width=True):
            st.success("Assistant deployment initiated!")
    
    with col2:
        if st.button("🔄 Refresh All Services", use_container_width=True):
            st.info("Services refreshed successfully!")
    
    with col3:
        if st.button("📈 View Analytics", use_container_width=True):
            st.info("Analytics dashboard coming soon!")
    
    st.subheader("📊 System Status")
    
    # Status cards
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4>🔗 Backend Services</h4>
            <span class="status-badge status-success">✓ API Server Running</span><br>
            <span class="status-badge status-success">✓ Database Connected</span><br>
            <span class="status-badge status-warning">⚠ High Memory Usage</span>
        </div>
        """, unsafe_allow_html=True)
    
    with status_col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4>🤖 Assistant Status</h4>
            <span class="status-badge status-success">✓ Assistant-1 Active</span><br>
            <span class="status-badge status-success">✓ Assistant-2 Active</span><br>
            <span class="status-badge status-info">⏸ Assistant-3 Paused</span>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.subheader("🤖 Assistant Management")
    
    # Sample assistant data
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h4 style="margin: 0; color: #2c3e50;">Customer Support Assistant</h4>
                <p style="margin: 0.5rem 0; color: #6c757d;">Handles customer inquiries and support tickets</p>
            </div>
            <span class="status-badge status-success">✓ Active</span>
        </div>
        <hr style="margin: 1rem 0;">
        <p><strong>Plugins:</strong> <span class="status-badge status-info">Email</span> <span class="status-badge status-info">Slack</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h4 style="margin: 0; color: #2c3e50;">Data Analysis Assistant</h4>
                <p style="margin: 0.5rem 0; color: #6c757d;">Processes and analyzes business data</p>
            </div>
            <span class="status-badge status-success">✓ Active</span>
        </div>
        <hr style="margin: 1rem 0;">
        <p><strong>Plugins:</strong> <span class="status-badge status-info">Database</span> <span class="status-badge status-info">Charts</span></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("➕ Add New Assistant", use_container_width=True):
        st.success("New assistant configuration panel would open here!")

with tab3:
    st.subheader("🔌 Plugin Marketplace")
    
    plugin_col1, plugin_col2, plugin_col3 = st.columns(3)
    
    with plugin_col1:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4>📧 Email Plugin</h4>
            <p>Send and receive emails through assistants</p>
            <span class="status-badge status-success">✓ Installed</span>
        </div>
        """, unsafe_allow_html=True)
    
    with plugin_col2:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4>📊 Analytics Plugin</h4>
            <p>Advanced data analytics and reporting</p>
            <span class="status-badge status-info">📥 Available</span>
        </div>
        """, unsafe_allow_html=True)
    
    with plugin_col3:
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4>🔗 API Plugin</h4>
            <p>Connect to external APIs and services</p>
            <span class="status-badge status-warning">🔄 Update Available</span>
        </div>
        """, unsafe_allow_html=True)

with tab4:
    st.subheader("📋 System Logs")
    
    # Log entries with modern styling
    logs = [
        {"level": "INFO", "time": "2024-01-20 10:30:15", "message": "Assistant-1 started successfully", "module": "core.assistant"},
        {"level": "WARNING", "time": "2024-01-20 10:28:42", "message": "High memory usage detected", "module": "system.monitor"},
        {"level": "INFO", "time": "2024-01-20 10:25:33", "message": "Email plugin activated", "module": "plugins.email"},
        {"level": "ERROR", "time": "2024-01-20 10:20:15", "message": "Database connection timeout", "module": "database.connection"},
    ]
    
    for log in logs:
        level_class = {
            "INFO": "status-info",
            "WARNING": "status-warning", 
            "ERROR": "status-error",
            "DEBUG": "status-success"
        }.get(log["level"], "status-info")
        
        st.markdown(f"""
        <div style="background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 0.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1;">
                    <span class="status-badge {level_class}">{log["level"]}</span>
                    <strong style="margin-left: 1rem;">{log["message"]}</strong>
                </div>
                <div style="text-align: right; color: #6c757d; font-size: 0.875rem;">
                    <div>{log["time"]}</div>
                    <div style="font-size: 0.75rem;">{log["module"]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 1rem; color: white;">
        <h2>🤖 Dingent</h2>
        <p style="opacity: 0.8;">Admin Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    if st.button("💾 Save Configuration", use_container_width=True):
        st.success("Configuration saved!")
    
    if st.button("⚙️ Settings", use_container_width=True):
        st.info("Settings panel would open here!")
    
    st.markdown("---")
    
    st.markdown("""
    <div style="color: white; opacity: 0.7; text-align: center; font-size: 0.875rem;">
        <p>🔗 Backend Status</p>
        <span class="status-badge status-success">✓ Connected</span>
    </div>
    """, unsafe_allow_html=True)