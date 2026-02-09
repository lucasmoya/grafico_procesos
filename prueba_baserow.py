import requests
from typing import Dict, Any, Optional, List

# ================= CONFIG =================

BASE_URL = "https://api.baserow.io/api/database"
TABLE_ID = 831016
TOKEN = "ZISPLMNCZbn5yuZ0BRRDfUdVIK8ITNXv"  # 🔥 REEMPLAZAR

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json",
}

# =========================================


class BaserowProcesos:
    def __init__(self, table_id: int = TABLE_ID):
        self.table_id = table_id

    # ---------------- LISTAR CAMPOS ----------------
    def get_fields(self):
        url = f"{BASE_URL}/fields/table/{self.table_id}/"
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()

    # ---------------- LISTAR FILAS ----------------
    def list_rows(
        self,
        page: int = 1,
        size: int = 100,
        user_field_names: bool = True,
        order_by: Optional[str] = None,
        filters: Optional[Dict] = None,
    ):
        params = {
            "page": page,
            "size": size,
        }
        if user_field_names:
            params["user_field_names"] = "true"
        if order_by:
            params["order_by"] = order_by
        if filters:
            params["filters"] = filters

        url = f"{BASE_URL}/rows/table/{self.table_id}/"
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()

    # ---------------- OBTENER FILA ----------------
    def get_row(self, row_id: int, user_field_names: bool = True):
        params = {}
        if user_field_names:
            params["user_field_names"] = "true"

        url = f"{BASE_URL}/rows/table/{self.table_id}/{row_id}/"
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        return r.json()

    # ---------------- CREAR FILA ----------------
    def create_row(self, data: Dict[str, Any], user_field_names: bool = True):
        params = {}
        if user_field_names:
            params["user_field_names"] = "true"

        url = f"{BASE_URL}/rows/table/{self.table_id}/"
        r = requests.post(url, headers=HEADERS, params=params, json=data)
        r.raise_for_status()
        return r.json()


# ================= EJEMPLOS =================
if __name__ == "__main__":
    api = BaserowProcesos()

    # 1️⃣ Listar campos
    fields = api.get_fields()
    print("FIELDS:", fields)

    # 2️⃣ Listar primeras 10 filas
    rows = api.list_rows(page=1, size=10)
    print("ROWS:", rows)

    # 3️⃣ Obtener fila específica
    # row = api.get_row(1)
    # print("ROW 1:", row)
