"""
Streamlit Dashboard for Doris Data Analysis
Automatically connects to Doris, analyzes tables, and generates insights
"""

import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from local_config import DORIS_CONFIG

# Override with actual Doris host for local dashboard
DORIS_CONFIG = {
    'host': 'localhost',  # Try localhost since Doris might be running locally
    'port': 9030,
    'user': 'root',
    'password': '',
    'database': 'updated_test2'
}

# Page configuration
st.set_page_config(
    page_title="Doris Data Insights Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .insight-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_doris_connection():
    """Establish connection to Doris database"""
    try:
        conn = pymysql.connect(
            host=DORIS_CONFIG["host"],
            port=DORIS_CONFIG["port"],
            user=DORIS_CONFIG["user"],
            password=DORIS_CONFIG["password"],
            database=DORIS_CONFIG["database"],
            charset='utf8mb4'
        )
        return conn
    except Exception as e:
        st.error(f"❌ Failed to connect to Doris: {e}")
        return None

@st.cache_data(ttl=60)
def get_all_tables(_conn):
    """Get list of all tables in the database"""
    try:
        query = "SHOW TABLES"
        df = pd.read_sql(query, _conn)
        return df.iloc[:, 0].tolist()
    except Exception as e:
        st.error(f"Error fetching tables: {e}")
        return []

@st.cache_data(ttl=60)
def get_table_info(_conn, table_name):
    """Get table schema and row count"""
    try:
        # Get row count
        count_query = f"SELECT COUNT(*) as count FROM `{table_name}`"
        count_df = pd.read_sql(count_query, _conn)
        row_count = count_df['count'].iloc[0]
        
        # Get schema
        schema_query = f"DESC `{table_name}`"
        schema_df = pd.read_sql(schema_query, _conn)
        
        return row_count, schema_df
    except Exception as e:
        st.error(f"Error fetching info for {table_name}: {e}")
        return 0, pd.DataFrame()

@st.cache_data(ttl=60)
def get_table_data(_conn, table_name, limit=10000):
    """Fetch data from a table"""
    try:
        query = f"SELECT * FROM `{table_name}` LIMIT {limit}"
        df = pd.read_sql(query, _conn)
        return df
    except Exception as e:
        st.error(f"Error fetching data from {table_name}: {e}")
        return pd.DataFrame()

def analyze_column(series):
    """Generate insights for a single column"""
    insights = []
    col_name = series.name
    
    # Null analysis
    null_count = series.isnull().sum()
    null_pct = (null_count / len(series)) * 100
    if null_pct > 0:
        insights.append(f"⚠️ {null_pct:.1f}% missing values ({null_count:,} rows)")
    
    # Numeric analysis
    if pd.api.types.is_numeric_dtype(series):
        non_null = series.dropna()
        if len(non_null) > 0:
            insights.append(f"📊 Range: {non_null.min():,.2f} to {non_null.max():,.2f}")
            insights.append(f"📈 Mean: {non_null.mean():,.2f} | Median: {non_null.median():,.2f}")
            
            # Detect outliers (values beyond 3 standard deviations)
            std = non_null.std()
            mean = non_null.mean()
            outliers = non_null[(non_null < mean - 3*std) | (non_null > mean + 3*std)]
            if len(outliers) > 0:
                insights.append(f"🚨 {len(outliers)} outliers detected (±3σ)")
    
    # Categorical analysis
    elif pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        non_null = series.dropna()
        unique_count = non_null.nunique()
        insights.append(f"🔢 {unique_count:,} unique values")
        
        if unique_count <= 10 and len(non_null) > 0:
            top_value = non_null.value_counts().iloc[0]
            top_name = non_null.value_counts().index[0]
            insights.append(f"🔥 Most frequent: '{top_name}' ({top_value:,} times)")
    
    # Duplicate analysis
    dup_count = series.duplicated().sum()
    if dup_count > 0:
        dup_pct = (dup_count / len(series)) * 100
        insights.append(f"📋 {dup_pct:.1f}% duplicate values")
    
    return insights

def generate_visualizations(df, table_name):
    """Generate automatic visualizations based on data types"""
    st.markdown(f"### 📊 Visualizations for `{table_name}`")
    
    # Separate numeric and categorical columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    # Numeric distributions
    if numeric_cols:
        st.markdown("#### 📈 Numeric Distributions")
        cols = st.columns(min(2, len(numeric_cols)))
        for idx, col in enumerate(numeric_cols[:4]):  # Show first 4
            with cols[idx % 2]:
                fig = px.histogram(df, x=col, title=f"Distribution of {col}",
                                 marginal="box", nbins=30)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
    
    # Categorical distributions
    if categorical_cols:
        st.markdown("#### 🏷️ Categorical Distributions")
        cols = st.columns(min(2, len(categorical_cols)))
        for idx, col in enumerate(categorical_cols[:4]):  # Show first 4
            with cols[idx % 2]:
                value_counts = df[col].value_counts().head(10)
                fig = px.bar(x=value_counts.index, y=value_counts.values,
                           title=f"Top 10 Values in {col}",
                           labels={'x': col, 'y': 'Count'})
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
    
    # Correlation heatmap for numeric columns
    if len(numeric_cols) >= 2:
        st.markdown("#### 🔥 Correlation Heatmap")
        corr_matrix = df[numeric_cols].corr()
        fig = px.imshow(corr_matrix, 
                       text_auto=True,
                       aspect="auto",
                       color_continuous_scale='RdBu_r',
                       title="Feature Correlations")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def generate_table_insights(df, table_name):
    """Generate comprehensive insights for a table"""
    st.markdown(f"### 🔍 Insights for `{table_name}`")
    
    total_rows = len(df)
    total_cols = len(df.columns)
    
    # Overall statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Rows", f"{total_rows:,}")
    with col2:
        st.metric("Total Columns", total_cols)
    with col3:
        total_nulls = df.isnull().sum().sum()
        st.metric("Missing Values", f"{total_nulls:,}")
    with col4:
        memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        st.metric("Memory Usage", f"{memory_mb:.2f} MB")
    
    st.markdown("---")
    
    # Column-wise insights
    st.markdown("#### 📋 Column-Wise Analysis")
    
    for col in df.columns:
        with st.expander(f"**{col}** ({df[col].dtype})"):
            insights = analyze_column(df[col])
            if insights:
                for insight in insights:
                    st.markdown(f"<div class='insight-box'>{insight}</div>", 
                              unsafe_allow_html=True)
            else:
                st.info("No specific insights for this column")
    
    # Data quality score
    st.markdown("#### ✅ Data Quality Score")
    null_score = 100 - (df.isnull().sum().sum() / (total_rows * total_cols) * 100)
    dup_score = 100 - (df.duplicated().sum() / total_rows * 100)
    overall_score = (null_score + dup_score) / 2
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Completeness", f"{null_score:.1f}%", 
                 help="Percentage of non-null values")
    with col2:
        st.metric("Uniqueness", f"{dup_score:.1f}%",
                 help="Percentage of unique rows")
    with col3:
        quality_color = "🟢" if overall_score >= 80 else "🟡" if overall_score >= 60 else "🔴"
        st.metric("Overall Quality", f"{quality_color} {overall_score:.1f}%")

def show_pipeline_metrics(conn):
    """Show pipeline statistics from all tables"""
    st.markdown("### 🚀 Pipeline Overview")
    
    tables = get_all_tables(conn)
    
    if not tables:
        st.warning("No tables found in the database")
        return
    
    # Aggregate metrics
    total_rows = 0
    total_tables = len(tables)
    
    table_stats = []
    for table in tables:
        row_count, schema = get_table_info(conn, table)
        total_rows += row_count
        table_stats.append({
            'Table': table,
            'Rows': row_count,
            'Columns': len(schema)
        })
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Tables", total_tables)
    with col2:
        st.metric("📈 Total Rows", f"{total_rows:,}")
    with col3:
        avg_rows = total_rows / total_tables if total_tables > 0 else 0
        st.metric("📊 Avg Rows/Table", f"{avg_rows:,.0f}")
    
    st.markdown("---")
    
    # Table statistics
    st.markdown("#### 📋 Table Statistics")
    stats_df = pd.DataFrame(table_stats)
    stats_df = stats_df.sort_values('Rows', ascending=False)
    
    # Bar chart
    fig = px.bar(stats_df, x='Table', y='Rows', 
                title="Rows per Table",
                color='Rows',
                color_continuous_scale='viridis')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.dataframe(stats_df, use_container_width=True, hide_index=True)

# Main application
def main():
    # Header
    st.markdown("<div class='main-header'>📊 Doris Data Insights Dashboard</div>", 
               unsafe_allow_html=True)
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    st.markdown("---")
    
    # Connect to database
    conn = get_doris_connection()
    if not conn:
        st.stop()
    
    # Sidebar
    st.sidebar.title("⚙️ Dashboard Controls")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Get tables
    tables = get_all_tables(conn)
    
    if not tables:
        st.warning("⚠️ No tables found in the database. Run the pipeline first!")
        st.stop()
    
    # Sidebar options
    view_mode = st.sidebar.radio(
        "📊 View Mode",
        ["Pipeline Overview", "Table Analysis"],
        index=0
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔗 Database Info")
    st.sidebar.info(f"""
    **Host:** {DORIS_CONFIG['host']}  
    **Database:** {DORIS_CONFIG['database']}  
    **Tables:** {len(tables)}
    """)
    
    # Main content
    if view_mode == "Pipeline Overview":
        show_pipeline_metrics(conn)
        
    else:  # Table Analysis
        st.sidebar.markdown("---")
        selected_table = st.sidebar.selectbox(
            "🗂️ Select Table",
            tables,
            index=0
        )
        
        # Fetch data
        with st.spinner(f"Loading data from `{selected_table}`..."):
            df = get_table_data(conn, selected_table)
        
        if df.empty:
            st.warning(f"No data found in table `{selected_table}`")
            st.stop()
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Insights", "📈 Visualizations", "🗃️ Raw Data"])
        
        with tab1:
            generate_table_insights(df, selected_table)
        
        with tab2:
            generate_visualizations(df, selected_table)
        
        with tab3:
            st.markdown(f"### 🗃️ Raw Data from `{selected_table}`")
            st.markdown(f"*Showing first 10,000 rows*")
            st.dataframe(df, use_container_width=True, height=600)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "🚀 Powered by Doris + Streamlit | Auto-refreshes every 60 seconds"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
