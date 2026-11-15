HEAD_ADMIN = "Head Admin"
ADMIN = "Admin"
SUPPORT_STAFF = "Support Staff"
SUPER_ADMIN = "Super Admin"  # top authority; manages every account, including Head Admins
RIDER = "Rider"              # deliveries only
DEVELOPER = "Developer"      # technical diagnostics only; never customer, payment, or admin-security data
# Retired: the Distributor role no longer exists. Old accounts keep their record but have no access
# until a Head Admin gives them another role.
RETIRED_DISTRIBUTOR = "Distributor"
CONTENT_MANAGER = "Content Manager"  # an older role: kept working, not offered for new accounts

# "Super Admin" accounts (from the original seed) keep full access.
LEGACY_HEAD_ROLES = {"Super Admin"}
HEAD_ROLES = {HEAD_ADMIN} | LEGACY_HEAD_ROLES

ASSIGNABLE_ROLES = [SUPER_ADMIN, HEAD_ADMIN, ADMIN, SUPPORT_STAFF, RIDER, DEVELOPER]

# Higher number = more authority. Equal or higher rank can never be managed by a lower one.
RANKS = {SUPER_ADMIN: 5, HEAD_ADMIN: 4, ADMIN: 3, SUPPORT_STAFF: 2, CONTENT_MANAGER: 2, RIDER: 1, DEVELOPER: 1, RETIRED_DISTRIBUTOR: 0}


def rank_of(role):
    return RANKS.get(role, 0)

# What a Head Admin can switch on for other accounts. Admin accounts and payment
# settings are always Head Admin only.
PERMISSIONS = {
    "products": "Manage products and run sales or discounts",
    "services": "Manage services, areas and prices, and service requests",
    "orders": "View orders",
    "manage_orders": "Confirm, ship and manage orders, payments, returns and refunds",
    "customers": "View and manage customer accounts",
    "chatbot": "Manage the chatbot knowledge base and chat monitor",
    "livechat": "Answer customers in live chat",
    "analytics": "View sales reports and estimates",
    "deliveries": "Deliver assigned orders and upload delivery proof (riders only)",
    "diagnostics": "View technical diagnostics and health checks (developers only)",
}

# Starting permissions for a role. A Head Admin can change them per account.
ROLE_PRESETS = {
    ADMIN: list(PERMISSIONS),
    SUPPORT_STAFF: ["orders", "manage_orders", "customers", "chatbot", "livechat"],
    CONTENT_MANAGER: ["products", "services", "analytics", "chatbot"],
    RETIRED_DISTRIBUTOR: [],
    RIDER: ["deliveries"],
    DEVELOPER: ["diagnostics"],
}


def is_head_role(role):
    return role in HEAD_ROLES


# Field-level data (customers, payments, sales) is never given to riders or developers.
ROLE_ONLY = {"deliveries": RIDER, "diagnostics": DEVELOPER}


def allowed_permissions(role):
    if is_head_role(role):
        return list(PERMISSIONS)
    if role == RIDER:
        return ["deliveries"]
    if role == DEVELOPER:
        return ["diagnostics"]
    return [key for key in PERMISSIONS if key not in ROLE_ONLY]


def clean_permissions(values, role=None):
    """Known keys only, no duplicates, stable order, and only what the role may hold."""
    if role in (RIDER, DEVELOPER):
        return list(ROLE_PRESETS[role])  # fixed: riders and developers get exactly their preset
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
        }
        for role in ASSIGNABLE_ROLES
    }
