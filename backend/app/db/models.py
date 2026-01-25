from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager')", name='users_role_check'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Unit(Base):
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True)
    flat_number = Column(String(20), nullable=False)
    building_name = Column(String(100), nullable=False)
    
    tenants = relationship("Tenant", back_populates="unit")
    
    def __repr__(self):
        return f"<Unit(id={self.id}, flat={self.flat_number}, building={self.building_name})>"


class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"))
    
    unit = relationship("Unit", back_populates="tenants")
    complaints = relationship("Complaint", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, phone={self.phone})>"


class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"))
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)
    source = Column(String(20), nullable=False, server_default="AI_AGENT")
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    tenant = relationship("Tenant", back_populates="complaints")
    call_log = relationship("CallLog", back_populates="complaint", uselist=False)
    
    def __repr__(self):
        return f"<Complaint(id={self.id}, category={self.category}, status={self.status})>"


class CallLog(Base):
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), nullable=False)
    transcript = Column(Text, nullable=False)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"))
    
    complaint = relationship("Complaint", back_populates="call_log")
    
    def __repr__(self):
        return f"<CallLog(id={self.id}, phone={self.phone_number})>"
