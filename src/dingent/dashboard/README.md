# Dingent Admin Dashboard - React-style Frontend

This directory contains the new React-style admin dashboard frontend for Dingent, built using modern web technologies and design principles.

## Overview

The original Streamlit dashboard has been replaced with a modern, React-inspired interface that provides:

- **Modern UI/UX**: Clean, professional design with card-based layouts
- **Responsive Design**: Works on desktop, tablet, and mobile devices  
- **Enhanced Navigation**: Intuitive tabbed interface with sidebar controls
- **Status Monitoring**: Real-time system status with color-coded indicators
- **Interactive Components**: Modern buttons, cards, and layout elements

## Features

### Dashboard Overview
- System metrics with visual indicators
- Quick action buttons for common tasks
- Real-time status monitoring
- Connection status indicators

### Assistant Management
- Visual assistant cards with status badges
- Plugin management interface
- Easy enable/disable controls
- Add new assistant functionality

### Plugin Marketplace
- Plugin installation status
- Available plugins browsing
- Update notifications
- Plugin descriptions and features

### System Logs
- Colored log level indicators
- Structured log display
- Timestamp and module information
- Real-time log monitoring

## Files

- `modern_app.py` - Main Streamlit application with React-style UI
- `web/index.html` - Pure HTML/JS dashboard (alternative implementation)
- `web_server.py` - Simple Python web server for serving the HTML dashboard

## Usage

### Option 1: Enhanced Streamlit Dashboard (Recommended)
```bash
# Start the modern Streamlit dashboard
streamlit run src/dingent/dashboard/modern_app.py --server.port=8503
```

### Option 2: Pure HTML/JS Dashboard
```bash
# Start the web server
python src/dingent/dashboard/web_server.py
```

## API Integration

The dashboard connects to the existing backend API endpoints:

- `/assistants` - Assistant configuration management
- `/plugins` - Plugin management  
- `/app_settings` - Application settings
- `/logs` - System logging
- `/logs/statistics` - Log statistics and metrics

## Design Features

- **Color Scheme**: Professional blue gradient theme (#667eea to #764ba2)
- **Typography**: Modern sans-serif fonts with proper hierarchy
- **Cards**: Elevated cards with subtle shadows for content organization
- **Status Badges**: Color-coded status indicators (success, warning, error, info)
- **Responsive Grid**: Flexible column layouts that adapt to screen size
- **Interactive Elements**: Hover effects and smooth transitions

## Comparison with Original

| Feature | Original Streamlit | New React-style |
|---------|-------------------|------------------|
| Design | Basic Streamlit theme | Modern card-based design |
| Navigation | Simple tabs | Enhanced tabbed interface with sidebar |
| Status Display | Text-based | Color-coded badges and indicators |
| Responsiveness | Limited | Fully responsive design |
| Visual Hierarchy | Basic | Professional with clear hierarchy |
| User Experience | Functional | Modern and intuitive |

## Future Enhancements

- Real-time WebSocket updates
- Advanced filtering and search
- Dark/light theme toggle
- Accessibility improvements
- Performance optimizations
- Additional chart and visualization components