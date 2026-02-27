from sqlalchemy import Enum
import enum
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPPORT_AGENT = "support_agent"
    TEAM_LEAD = "team_lead"
    

class ContactMode(str, enum.Enum):
    EMAIL = "email"
    PORTAL = "portal"
