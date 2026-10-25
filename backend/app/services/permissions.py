HEAD_ADMIN = "Head Admin"
ADMIN = "Admin"
SUPPORT_STAFF = "Support Staff"
DISTRIBUTOR = "Distributor"
CONTENT_MANAGER = "Content Manager"  # an older role: kept working, not offered for new accounts

# "Super Admin" accounts (from the original seed) keep full access.
LEGACY_HEAD_ROLES = {"Super Admin"}
HEAD_ROLES = {HEAD_ADMIN} | LEGACY_HEAD_ROLES

ASSIGNABLE_ROLES = [HEAD_ADMIN, ADMIN, SUPPORT_STAFF, DISTRIBUTOR]

# What a Head Admin can switch on for other accounts. Admin accounts and payment
# settings are always Head Admin only.
PERMISSIONS = {
    "products": "Manage products and run sales or discounts",
    "services": "Manage services, areas and prices, and service requests",
    "orders": "View orders",
    "manage_orders": "Confirm, ship and manage orders, payments, returns and refunds",
    "customers": "View and manage customer accounts",
    "chatbot": "Manage the chatbot knowledge base and chat monitor",
    "analytics": "View sales reports and estimates",
}

# A distributor is limited to their own products and cannot be given the wider permissions.
DISTRIBUTOR_ALLOWED = ["products", "services", "orders", "analytics"]

# Starting permissions for a role. A Head Admin can change them per account.
ROLE_PRESETS = {
    ADMIN: list(PERMISSIONS),
    SUPPORT_STAFF: ["orders", "manage_orders", "customers", "chatbot"],
    CONTENT_MANAGER: ["products", "services", "analytics", "chatbot"],
    DISTRIBUTOR: [],
}


def is_head_role(role):
    return role in HEAD_ROLES


def allowed_permissions(role):
    if is_head_role(role):
        return list(PERMISSIONS)
    if role == DISTRIBUTOR:
        return list(DISTRIBUTOR_ALLOWED)
    return list(PERMISSIONS)


def clean_permissions(values, role=None):
    """Known keys only, no duplicates, stable order, and only what the role may hold."""
    allowed = set(allowed_permissions(role)) if role else set(PERMISSIONS)
    wanted = set(values or [])
    return [key for key in PERMISSIONS if key in wanted and key in allowed]


def default_permissions(role):
    return list(ROLE_PRESETS.get(role, []))


def role_info():
    """For the account form: what each role may hold and what it starts with."""
    return {
        role: {
            "allowed": allowed_permissions(role),
            "preset": default_permissions(role),
            "scoped": role == DISTRIBUTOR,
        }
        for role in ASSIGNABLE_ROLES
    }
