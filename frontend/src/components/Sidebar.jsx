import React from 'react';
import './Sidebar.css';

const Sidebar = () => {
    return (
        <div className="sidebar">
            <div className="sidebar-header">
                <h1 className="brand">M-TENANT</h1>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-item">
                    <span className="nav-icon">👤</span>
                    <span className="nav-text">Profile</span>
                </div>

                <div className="nav-item active">
                    <span className="nav-icon">📊</span>
                    <span className="nav-text">Dashboard</span>
                </div>

                <div className="nav-item">
                    <span className="nav-icon">🚪</span>
                    <span className="nav-text">Logout</span>
                </div>
            </nav>

            <div className="sidebar-footer">
                <div className="service-badge">
                    <div className="service-icon">
                        <div className="service-text">24/7</div>
                        <div className="service-subtext">SERVICE</div>
                    </div>
                </div>
                <div className="service-illustration">
                    <div className="person-working">
                        <div className="person-head"></div>
                        <div className="person-body"></div>
                        <div className="laptop"></div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
