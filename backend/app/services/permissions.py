HEAD_ADMIN = "Head Admin"
DISTRIBUTOR = "Distributor"

# Accounts created before roles existed keep full access under their old names.
LEGACY_HEAD_ROLES = {"Super Admin", "Admin"}
HEAD_ROLES = {HEAD_ADMIN} | LEGACY_HEAD_ROLES

ASSIGNABLE_ROLES = [HEAD_ADMIN, DISTRIBUTOR]

# What a Head Admin can grant to a distributor. Everything else is Head Admin only.
PERMISSIONS = {
    "products": "Add and manage their own products",
    "services": "Add and manage their own services, areas and prices",
    "orders": "View orders that contain their own products",
    "analytics": "View sales reports for their own products",
}


def is_head_role(role):
    return role in HEAD_ROLES


def clean_permissions(values):
    """Keeps only known permission keys, without duplicates, in a stable order."""
    wanted = set(values or [])
    return [key for key in PERMISSIONS if key in wanted]
