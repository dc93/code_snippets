"""
System settings model
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from .database import Base


class SystemSettings(Base):
    """
    Key-value store for system settings.
    These override config.py defaults and can be changed at runtime.
    """
    __tablename__ = 'system_settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default='string', nullable=False)  # string, int, bool, json
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)  # general, paths, quality, etc.

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_modified_by = Column(String(100), default='system', nullable=False)

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'

    def get_typed_value(self):
        """Get value with correct type conversion."""
        if self.value is None:
            return None

        if self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'bool':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value

    @staticmethod
    def get_setting(session, key, default=None):
        """Get a setting value by key."""
        setting = session.query(SystemSettings).filter_by(key=key).first()
        if setting:
            return setting.get_typed_value()
        return default

    @staticmethod
    def set_setting(session, key, value, value_type='string', description=None, category=None):
        """Set a setting value."""
        setting = session.query(SystemSettings).filter_by(key=key).first()

        # Convert value to string for storage
        if value_type == 'json':
            import json
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        if setting:
            setting.value = value_str
            setting.value_type = value_type
            if description:
                setting.description = description
            if category:
                setting.category = category
        else:
            setting = SystemSettings(
                key=key,
                value=value_str,
                value_type=value_type,
                description=description,
                category=category
            )
            session.add(setting)

        session.commit()
        return setting

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.get_typed_value(),
            'value_type': self.value_type,
            'description': self.description,
            'category': self.category,
        }
