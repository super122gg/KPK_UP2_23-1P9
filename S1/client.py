"""
client.py — Auth Service Desktop Client (tkinter + requests)
Запуск: python client.py
Требует: pip install requests
Сервис должен быть запущен: uvicorn service:app --reload
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import requests

API_BASE_URL = "http://localhost:8000"

# ─────────────────────────────────────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────────────────────────────────────

def api_call(method, path, **kwargs):
    """Выполнить HTTP-запрос к API. Возвращает Response или None при ошибке."""
    try:
        response = getattr(requests, method)(API_BASE_URL + path, **kwargs)
        return response
    except requests.exceptions.ConnectionError:
        messagebox.showerror(
            "Ошибка подключения",
            "Не удалось подключиться к сервису.\n"
            "Убедитесь, что service.py запущен на " + API_BASE_URL
        )
        return None
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))
        return None


def get_detail(response):
    """Извлечь текст ошибки из ответа API."""
    try:
        return str(response.json().get("detail", response.text))
    except Exception:
        return response.text


def show_api_error(response):
    """Показать сообщение об ошибке API."""
    messagebox.showerror(
        "Ошибка " + str(response.status_code),
        get_detail(response)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Главное приложение
# ─────────────────────────────────────────────────────────────────────────────

class App:
    """Главный класс приложения. Все методы API вызываются отсюда."""

    def __init__(self, root):
        self.root = root
        self.root.title("Auth Service — S1")
        self.root.geometry("1000x660")
        self.root.configure(bg="#f0f2f5")
        self._build_header()
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self._build_users_tab()
        self._build_auth_tab()
        self._build_tokens_tab()

    # ══════════════════════════════════════════════════════════════════════════
    # Шапка
    # ══════════════════════════════════════════════════════════════════════════

    def _build_header(self):
        bar = tk.Frame(self.root, bg="#2c3e6b", height=44)
        bar.pack(fill=tk.X)
        tk.Label(bar, text="🔐  Auth Service  |  S1",
                 bg="#2c3e6b", fg="white",
                 font=("Arial", 13, "bold")).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(bar, text="API: " + API_BASE_URL,
                 bg="#2c3e6b", fg="#9ab4d8",
                 font=("Arial", 9)).pack(side=tk.RIGHT, padx=14)

    # ══════════════════════════════════════════════════════════════════════════
    # Вкладка 1: Пользователи  (POST/PUT/DELETE/GET /users/)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_users_tab(self):
        tab = tk.Frame(self._notebook, bg="#f0f2f5")
        self._notebook.add(tab, text="👤 Пользователи")

        # ── Панель кнопок ─────────────────────────────────────────────────────
        btn_bar = tk.LabelFrame(tab, text="Операции", bg="#f0f2f5",
                                font=("Arial", 9, "bold"))
        btn_bar.pack(fill=tk.X, padx=8, pady=6)

        s = {"bg": "#3b5998", "fg": "white", "relief": tk.FLAT,
             "font": ("Arial", 9), "padx": 9, "pady": 3, "cursor": "hand2"}

        tk.Button(btn_bar, text="➕ Создать",
                  command=self._user_create_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="✏️ Изменить",
                  command=self._user_update_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🗑 Удалить",
                  command=self._user_delete_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🔍 По ID",
                  command=self._user_get_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🔄 Обновить список",
                  command=self._users_load, **s).pack(side=tk.LEFT, padx=3, pady=5)

        # ── Фильтры ───────────────────────────────────────────────────────────
        flt = tk.LabelFrame(tab, text="Фильтры  GET /users/",
                            bg="#f0f2f5", font=("Arial", 9, "bold"))
        flt.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(flt, text="Логин:", bg="#f0f2f5").grid(
            row=0, column=0, padx=6, pady=4, sticky=tk.W)
        self._uf_login = tk.Entry(flt, width=18)
        self._uf_login.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(flt, text="Активен:", bg="#f0f2f5").grid(
            row=0, column=2, padx=6, pady=4, sticky=tk.W)
        self._uf_active = ttk.Combobox(flt, values=["", "true", "false"],
                                       width=7, state="readonly")
        self._uf_active.grid(row=0, column=3, padx=4, pady=4)
        self._uf_active.set("")

        tk.Button(flt, text="Применить", command=self._users_load, **s).grid(
            row=0, column=4, padx=8, pady=4)

        # ── Таблица ───────────────────────────────────────────────────────────
        tbl_frame = tk.Frame(tab)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        u_cols = ("id", "login", "is_active", "created_at", "updated_at")
        self._users_tree = ttk.Treeview(tbl_frame, columns=u_cols,
                                        show="headings", height=16)
        widths_u = {"id": 50, "login": 180, "is_active": 80,
                    "created_at": 170, "updated_at": 170}
        for col in u_cols:
            self._users_tree.heading(col, text=col)
            self._users_tree.column(col, width=widths_u.get(col, 140))

        vsb_u = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                              command=self._users_tree.yview)
        self._users_tree.configure(yscrollcommand=vsb_u.set)
        self._users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_u.pack(side=tk.LEFT, fill=tk.Y)

        self._users_load()

    def _users_load(self):
        """GET /users/ — список пользователей с фильтрами."""
        params = {}
        if self._uf_login.get().strip():
            params["login"] = self._uf_login.get().strip()
        if self._uf_active.get():
            params["is_active"] = self._uf_active.get()
        resp = api_call("get", "/users/", params=params)
        if resp is None:
            return
        if resp.status_code == 200:
            self._users_tree.delete(*self._users_tree.get_children())
            for u in resp.json():
                self._users_tree.insert("", tk.END, values=(
                    u["id"], u["login"], u["is_active"],
                    u["created_at"][:19], u["updated_at"][:19]))
        else:
            show_api_error(resp)

    def _users_selected_id(self):
        sel = self._users_tree.selection()
        return self._users_tree.item(sel[0])["values"][0] if sel else None

    def _user_create_dialog(self):
        """POST /users/ — создать пользователя."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Создать пользователя  POST /users/")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        tk.Label(dlg, text="Логин (3–150 симв.):", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W)
        e_login = tk.Entry(dlg, width=26)
        e_login.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Пароль (6–255 симв.):", bg="#f0f2f5").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W)
        e_pass = tk.Entry(dlg, width=26, show="*")
        e_pass.grid(row=1, column=1, padx=10, pady=6)

        def do_create():
            login = e_login.get().strip()
            password = e_pass.get()
            if len(login) < 3:
                messagebox.showwarning("Валидация", "Логин минимум 3 символа", parent=dlg)
                return
            if len(password) < 6:
                messagebox.showwarning("Валидация", "Пароль минимум 6 символов", parent=dlg)
                return
            resp = api_call("post", "/users/",
                            json={"login": login, "password": password})
            if resp is None:
                return
            if resp.status_code == 201:
                messagebox.showinfo(
                    "Готово",
                    "Пользователь создан.\nID = " + str(resp.json()["id"]),
                    parent=dlg)
                dlg.destroy()
                self._users_load()
            elif resp.status_code == 409:
                messagebox.showerror("Конфликт", "Логин уже занят", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка 400", get_detail(resp), parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Создать", command=do_create,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=2, column=0, columnspan=2, pady=10)

    def _user_update_dialog(self):
        """PUT /users/{id} — изменить пользователя."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Изменить пользователя  PUT /users/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._users_selected_id()

        tk.Label(dlg, text="ID пользователя:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=6, sticky=tk.W)
        if preselect:
            e_id.insert(0, str(preselect))

        tk.Label(dlg, text="Новый логин:", bg="#f0f2f5").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W)
        e_login = tk.Entry(dlg, width=26)
        e_login.grid(row=1, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Новый пароль:", bg="#f0f2f5").grid(
            row=2, column=0, padx=10, pady=6, sticky=tk.W)
        e_pass = tk.Entry(dlg, width=26, show="*")
        e_pass.grid(row=2, column=1, padx=10, pady=6)

        tk.Label(dlg, text="(оставьте пустым — не менять)",
                 bg="#f0f2f5", fg="#777", font=("Arial", 8)).grid(
            row=3, column=0, columnspan=2)

        def do_update():
            uid = e_id.get().strip()
            if not uid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            body = {}
            if e_login.get().strip():
                body["login"] = e_login.get().strip()
            if e_pass.get():
                body["password"] = e_pass.get()
            if not body:
                messagebox.showwarning("Валидация", "Нет данных для обновления", parent=dlg)
                return
            resp = api_call("put", "/users/" + uid, json=body)
            if resp is None:
                return
            if resp.status_code == 200:
                messagebox.showinfo("Готово", "Пользователь обновлён", parent=dlg)
                dlg.destroy()
                self._users_load()
            elif resp.status_code == 404:
                messagebox.showerror("Не найдено", "Пользователь не найден", parent=dlg)
            elif resp.status_code == 409:
                messagebox.showerror("Конфликт", "Логин уже занят", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка 400", get_detail(resp), parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Сохранить", command=do_update,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=4, column=0, columnspan=2, pady=10)

    def _user_delete_dialog(self):
        """DELETE /users/{id} — удалить пользователя (жёсткое)."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Удалить пользователя  DELETE /users/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._users_selected_id()

        tk.Label(dlg, text="ID пользователя:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if preselect:
            e_id.insert(0, str(preselect))

        def do_delete():
            uid = e_id.get().strip()
            if not uid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            if not messagebox.askyesno(
                "Подтверждение",
                "Удалить пользователя ID=" + uid + "?\nДействие необратимо.",
                parent=dlg):
                return
            resp = api_call("delete", "/users/" + uid)
            if resp is None:
                return
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    messagebox.showinfo("Готово", "Пользователь удалён", parent=dlg)
                    dlg.destroy()
                    self._users_load()
                else:
                    messagebox.showwarning("Не найдено", "Пользователь не найден", parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Удалить", command=do_delete,
                  bg="#c0392b", fg="white", relief=tk.FLAT, padx=14).grid(
            row=1, column=0, columnspan=2, pady=10)

    def _user_get_dialog(self):
        """GET /users/{id} — получить пользователя по ID."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Получить пользователя  GET /users/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._users_selected_id()

        tk.Label(dlg, text="ID пользователя:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if preselect:
            e_id.insert(0, str(preselect))

        out = tk.Text(dlg, height=7, width=48, state=tk.DISABLED, bg="#fafafa")
        out.grid(row=2, column=0, columnspan=2, padx=10, pady=6)

        def do_get():
            uid = e_id.get().strip()
            if not uid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            resp = api_call("get", "/users/" + uid)
            if resp is None:
                return
            out.config(state=tk.NORMAL)
            out.delete("1.0", tk.END)
            if resp.status_code == 200:
                u = resp.json()
                out.insert(tk.END,
                           "ID:         " + str(u["id"]) + "\n"
                           "Логин:      " + u["login"] + "\n"
                           "Активен:    " + str(u["is_active"]) + "\n"
                           "Создан:     " + u["created_at"][:19] + "\n"
                           "Изменён:    " + u["updated_at"][:19])
            elif resp.status_code == 404:
                out.insert(tk.END, "Пользователь не найден")
            else:
                out.insert(tk.END, "Ошибка " + str(resp.status_code) + ": " + get_detail(resp))
            out.config(state=tk.DISABLED)

        tk.Button(dlg, text="Найти", command=do_get,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=1, column=0, columnspan=2, pady=6)

    # ══════════════════════════════════════════════════════════════════════════
    # Вкладка 2: Аутентификация (login / reset-password)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_auth_tab(self):
        tab = tk.Frame(self._notebook, bg="#f0f2f5")
        self._notebook.add(tab, text="🔑 Аутентификация")

        # ── Вход ──────────────────────────────────────────────────────────────
        lf1 = tk.LabelFrame(tab, text="POST /auth/login — Вход",
                             bg="#f0f2f5", font=("Arial", 9, "bold"))
        lf1.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(lf1, text="Логин:", bg="#f0f2f5").grid(
            row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self._auth_login = tk.Entry(lf1, width=26)
        self._auth_login.grid(row=0, column=1, padx=8, pady=5)

        tk.Label(lf1, text="Пароль:", bg="#f0f2f5").grid(
            row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self._auth_pass = tk.Entry(lf1, width=26, show="*")
        self._auth_pass.grid(row=1, column=1, padx=8, pady=5)

        tk.Label(lf1, text="JWT-токен:", bg="#f0f2f5").grid(
            row=2, column=0, padx=8, pady=5, sticky=tk.W)
        self._auth_token_var = tk.StringVar(value="—")
        tk.Entry(lf1, textvariable=self._auth_token_var,
                 width=54, state="readonly", bg="#e8eef8").grid(
            row=2, column=1, padx=8, pady=5)

        tk.Button(lf1, text="Войти", command=self._do_login,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=12).grid(
            row=3, column=0, columnspan=2, pady=8)

        # ── Сброс пароля: шаг 1 ───────────────────────────────────────────────
        lf2 = tk.LabelFrame(
            tab, text="POST /auth/reset-password/request — Запрос токена сброса",
            bg="#f0f2f5", font=("Arial", 9, "bold"))
        lf2.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(lf2, text="Логин:", bg="#f0f2f5").grid(
            row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self._rr_login = tk.Entry(lf2, width=26)
        self._rr_login.grid(row=0, column=1, padx=8, pady=5)

        tk.Label(lf2, text="Токен (ответ):", bg="#f0f2f5").grid(
            row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self._rr_token_var = tk.StringVar(value="")
        tk.Entry(lf2, textvariable=self._rr_token_var,
                 width=54, state="readonly", bg="#e8eef8").grid(
            row=1, column=1, padx=8, pady=5)

        tk.Button(lf2, text="Запросить токен", command=self._do_reset_request,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=12).grid(
            row=2, column=0, columnspan=2, pady=8)

        # ── Сброс пароля: шаг 2 ───────────────────────────────────────────────
        lf3 = tk.LabelFrame(
            tab, text="POST /auth/reset-password/confirm — Применить новый пароль",
            bg="#f0f2f5", font=("Arial", 9, "bold"))
        lf3.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(lf3, text="Токен сброса:", bg="#f0f2f5").grid(
            row=0, column=0, padx=8, pady=5, sticky=tk.W)
        self._rc_token = tk.Entry(lf3, width=54)
        self._rc_token.grid(row=0, column=1, padx=8, pady=5)

        tk.Label(lf3, text="Новый пароль:", bg="#f0f2f5").grid(
            row=1, column=0, padx=8, pady=5, sticky=tk.W)
        self._rc_pass = tk.Entry(lf3, width=26, show="*")
        self._rc_pass.grid(row=1, column=1, padx=8, pady=5)

        tk.Button(lf3, text="Применить", command=self._do_reset_confirm,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=12).grid(
            row=2, column=0, columnspan=2, pady=8)

    def _do_login(self):
        """POST /auth/login"""
        login = self._auth_login.get().strip()
        password = self._auth_pass.get()
        if not login or not password:
            messagebox.showwarning("Валидация", "Заполните логин и пароль")
            return
        resp = api_call("post", "/auth/login",
                        json={"login": login, "password": password})
        if resp is None:
            return
        if resp.status_code == 200:
            self._auth_token_var.set(resp.json().get("access_token", ""))
            messagebox.showinfo("Успех", "Вход выполнен. JWT-токен получен.")
        elif resp.status_code == 401:
            messagebox.showerror("Ошибка 401", "Неверный логин или пароль")
        elif resp.status_code == 403:
            messagebox.showerror("Ошибка 403", "Аккаунт отключён")
        elif resp.status_code == 400:
            messagebox.showerror("Ошибка 400", get_detail(resp))
        else:
            show_api_error(resp)

    def _do_reset_request(self):
        """POST /auth/reset-password/request"""
        login = self._rr_login.get().strip()
        if not login:
            messagebox.showwarning("Валидация", "Введите логин")
            return
        resp = api_call("post", "/auth/reset-password/request",
                        json={"login": login})
        if resp is None:
            return
        if resp.status_code == 200:
            token = resp.json().get("token", "")
            self._rr_token_var.set(token)
            self._rc_token.delete(0, tk.END)
            self._rc_token.insert(0, token)
            messagebox.showinfo("Успех", "Токен создан и подставлен в поле ниже.")
        elif resp.status_code == 404:
            messagebox.showerror("Ошибка 404", "Пользователь не найден")
        elif resp.status_code == 409:
            messagebox.showerror("Ошибка 409",
                                 "Активный токен уже существует для этого пользователя")
        else:
            show_api_error(resp)

    def _do_reset_confirm(self):
        """POST /auth/reset-password/confirm"""
        token = self._rc_token.get().strip()
        new_pass = self._rc_pass.get()
        if not token or not new_pass:
            messagebox.showwarning("Валидация", "Заполните токен и новый пароль")
            return
        resp = api_call("post", "/auth/reset-password/confirm",
                        json={"token": token, "new_password": new_pass})
        if resp is None:
            return
        if resp.status_code == 200:
            messagebox.showinfo("Успех",
                                "Пароль изменён для: " + resp.json()["login"])
        elif resp.status_code == 400:
            detail = get_detail(resp)
            if "expired" in detail.lower():
                messagebox.showerror("Ошибка 400", "Токен истёк: " + detail)
            elif "used" in detail.lower():
                messagebox.showerror("Ошибка 400", "Токен уже использован: " + detail)
            else:
                messagebox.showerror("Ошибка 400", detail)
        elif resp.status_code == 404:
            messagebox.showerror("Ошибка 404", "Токен не найден")
        else:
            show_api_error(resp)

    # ══════════════════════════════════════════════════════════════════════════
    # Вкладка 3: Токены сброса пароля (POST/PUT/DELETE/GET /reset-tokens/)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tokens_tab(self):
        tab = tk.Frame(self._notebook, bg="#f0f2f5")
        self._notebook.add(tab, text="🗝 Токены сброса")

        # ── Панель кнопок ─────────────────────────────────────────────────────
        btn_bar = tk.LabelFrame(tab, text="Операции", bg="#f0f2f5",
                                font=("Arial", 9, "bold"))
        btn_bar.pack(fill=tk.X, padx=8, pady=6)

        s = {"bg": "#3b5998", "fg": "white", "relief": tk.FLAT,
             "font": ("Arial", 9), "padx": 9, "pady": 3, "cursor": "hand2"}

        tk.Button(btn_bar, text="➕ Создать",
                  command=self._token_create_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="✏️ Изменить",
                  command=self._token_update_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🗑 Удалить",
                  command=self._token_delete_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🔍 По ID",
                  command=self._token_get_dialog, **s).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(btn_bar, text="🔄 Обновить список",
                  command=self._tokens_load, **s).pack(side=tk.LEFT, padx=3, pady=5)

        # ── Фильтры ───────────────────────────────────────────────────────────
        flt = tk.LabelFrame(tab, text="Фильтры  GET /reset-tokens/",
                            bg="#f0f2f5", font=("Arial", 9, "bold"))
        flt.pack(fill=tk.X, padx=8, pady=2)

        tk.Label(flt, text="user_id:", bg="#f0f2f5").grid(
            row=0, column=0, padx=6, pady=4, sticky=tk.W)
        self._tf_uid = tk.Entry(flt, width=10)
        self._tf_uid.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(flt, text="Использован:", bg="#f0f2f5").grid(
            row=0, column=2, padx=6, pady=4, sticky=tk.W)
        self._tf_used = ttk.Combobox(flt, values=["", "true", "false"],
                                     width=7, state="readonly")
        self._tf_used.grid(row=0, column=3, padx=4, pady=4)
        self._tf_used.set("")

        tk.Button(flt, text="Применить", command=self._tokens_load, **s).grid(
            row=0, column=4, padx=8, pady=4)

        # ── Таблица ───────────────────────────────────────────────────────────
        tbl_frame = tk.Frame(tab)
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        t_cols = ("id", "user_id", "token", "expires_at", "is_used", "created_at")
        self._tokens_tree = ttk.Treeview(tbl_frame, columns=t_cols,
                                         show="headings", height=16)
        widths_t = {"id": 45, "user_id": 70, "token": 230,
                    "expires_at": 155, "is_used": 70, "created_at": 155}
        for col in t_cols:
            self._tokens_tree.heading(col, text=col)
            self._tokens_tree.column(col, width=widths_t.get(col, 120))

        vsb_t = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                              command=self._tokens_tree.yview)
        self._tokens_tree.configure(yscrollcommand=vsb_t.set)
        self._tokens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_t.pack(side=tk.LEFT, fill=tk.Y)

        self._tokens_load()

    def _tokens_load(self):
        """GET /reset-tokens/ — список токенов с фильтрами."""
        params = {}
        uid = self._tf_uid.get().strip()
        if uid.isdigit():
            params["user_id"] = int(uid)
        if self._tf_used.get():
            params["is_used"] = self._tf_used.get()
        resp = api_call("get", "/reset-tokens/", params=params)
        if resp is None:
            return
        if resp.status_code == 200:
            self._tokens_tree.delete(*self._tokens_tree.get_children())
            for t in resp.json():
                short = t["token"][:38] + ("…" if len(t["token"]) > 38 else "")
                self._tokens_tree.insert("", tk.END, values=(
                    t["id"], t["user_id"], short,
                    t["expires_at"][:19], t["is_used"], t["created_at"][:19]))
        else:
            show_api_error(resp)

    def _tokens_selected_id(self):
        sel = self._tokens_tree.selection()
        return self._tokens_tree.item(sel[0])["values"][0] if sel else None

    def _token_create_dialog(self):
        """POST /reset-tokens/ — создать токен сброса пароля."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Создать токен  POST /reset-tokens/")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        tk.Label(dlg, text="ID пользователя (user_id):", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W)
        e_uid = tk.Entry(dlg, width=12)
        e_uid.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Токен (пусто = авто):", bg="#f0f2f5").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W)
        e_token = tk.Entry(dlg, width=38)
        e_token.grid(row=1, column=1, padx=10, pady=6)

        default_exp = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(dlg, text="Срок действия (UTC):", bg="#f0f2f5").grid(
            row=2, column=0, padx=10, pady=6, sticky=tk.W)
        e_exp = tk.Entry(dlg, width=22)
        e_exp.grid(row=2, column=1, padx=10, pady=6, sticky=tk.W)
        e_exp.insert(0, default_exp)

        tk.Label(dlg, text="Формат: YYYY-MM-DD HH:MM:SS",
                 bg="#f0f2f5", fg="#777", font=("Arial", 8)).grid(
            row=3, column=0, columnspan=2)

        def do_create():
            uid_val = e_uid.get().strip()
            if not uid_val.isdigit():
                messagebox.showwarning("Валидация",
                                       "ID пользователя должен быть числом", parent=dlg)
                return
            import secrets as _sec
            token_val = e_token.get().strip() or _sec.token_urlsafe(32)
            exp_str = e_exp.get().strip()
            try:
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                messagebox.showwarning("Валидация",
                                       "Неверный формат даты", parent=dlg)
                return
            if exp_dt <= datetime.utcnow():
                messagebox.showwarning("Валидация",
                                       "Дата должна быть в будущем", parent=dlg)
                return
            resp = api_call("post", "/reset-tokens/", json={
                "user_id": int(uid_val),
                "token": token_val,
                "expires_at": exp_str.replace(" ", "T"),
            })
            if resp is None:
                return
            if resp.status_code == 201:
                messagebox.showinfo(
                    "Готово",
                    "Токен создан.\nID = " + str(resp.json()["id"]),
                    parent=dlg)
                dlg.destroy()
                self._tokens_load()
            elif resp.status_code == 404:
                messagebox.showerror("Ошибка 404", "Пользователь не найден", parent=dlg)
            elif resp.status_code == 409:
                messagebox.showerror("Ошибка 409", "Такой токен уже существует", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка 400", get_detail(resp), parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Создать", command=do_create,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=4, column=0, columnspan=2, pady=10)

    def _token_update_dialog(self):
        """PUT /reset-tokens/{id} — изменить токен (поле is_used)."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Изменить токен  PUT /reset-tokens/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._tokens_selected_id()

        tk.Label(dlg, text="ID токена:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=6, sticky=tk.W)
        if preselect:
            e_id.insert(0, str(preselect))

        tk.Label(dlg, text="is_used (отметить использованным):",
                 bg="#f0f2f5").grid(row=1, column=0, padx=10, pady=6, sticky=tk.W)
        used_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, variable=used_var, bg="#f0f2f5").grid(
            row=1, column=1, padx=10, pady=6, sticky=tk.W)

        def do_update():
            tid = e_id.get().strip()
            if not tid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            resp = api_call("put", "/reset-tokens/" + tid,
                            json={"is_used": used_var.get()})
            if resp is None:
                return
            if resp.status_code == 200:
                messagebox.showinfo("Готово", "Токен обновлён", parent=dlg)
                dlg.destroy()
                self._tokens_load()
            elif resp.status_code == 404:
                messagebox.showerror("Ошибка 404", "Токен не найден", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка 400", get_detail(resp), parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Сохранить", command=do_update,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=2, column=0, columnspan=2, pady=10)

    def _token_delete_dialog(self):
        """DELETE /reset-tokens/{id} — удалить токен (жёсткое)."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Удалить токен  DELETE /reset-tokens/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._tokens_selected_id()

        tk.Label(dlg, text="ID токена:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if preselect:
            e_id.insert(0, str(preselect))

        def do_delete():
            tid = e_id.get().strip()
            if not tid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            if not messagebox.askyesno(
                "Подтверждение",
                "Удалить токен ID=" + tid + "?",
                parent=dlg):
                return
            resp = api_call("delete", "/reset-tokens/" + tid)
            if resp is None:
                return
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    messagebox.showinfo("Готово", "Токен удалён", parent=dlg)
                    dlg.destroy()
                    self._tokens_load()
                else:
                    messagebox.showwarning("Не найдено", "Токен не найден", parent=dlg)
            else:
                show_api_error(resp)

        tk.Button(dlg, text="Удалить", command=do_delete,
                  bg="#c0392b", fg="white", relief=tk.FLAT, padx=14).grid(
            row=1, column=0, columnspan=2, pady=10)

    def _token_get_dialog(self):
        """GET /reset-tokens/{id} — получить токен по ID."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Получить токен  GET /reset-tokens/{id}")
        dlg.resizable(False, False)
        dlg.configure(bg="#f0f2f5")

        preselect = self._tokens_selected_id()

        tk.Label(dlg, text="ID токена:", bg="#f0f2f5").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W)
        e_id = tk.Entry(dlg, width=10)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if preselect:
            e_id.insert(0, str(preselect))

        out = tk.Text(dlg, height=8, width=52, state=tk.DISABLED, bg="#fafafa")
        out.grid(row=2, column=0, columnspan=2, padx=10, pady=6)

        def do_get():
            tid = e_id.get().strip()
            if not tid.isdigit():
                messagebox.showwarning("Валидация", "ID должен быть числом", parent=dlg)
                return
            resp = api_call("get", "/reset-tokens/" + tid)
            if resp is None:
                return
            out.config(state=tk.NORMAL)
            out.delete("1.0", tk.END)
            if resp.status_code == 200:
                t = resp.json()
                out.insert(tk.END,
                           "ID:          " + str(t["id"]) + "\n"
                           "user_id:     " + str(t["user_id"]) + "\n"
                           "token:       " + t["token"] + "\n"
                           "expires_at:  " + t["expires_at"][:19] + "\n"
                           "is_used:     " + str(t["is_used"]) + "\n"
                           "created_at:  " + t["created_at"][:19])
            elif resp.status_code == 404:
                out.insert(tk.END, "Токен не найден")
            else:
                out.insert(tk.END,
                           "Ошибка " + str(resp.status_code) + ": " + get_detail(resp))
            out.config(state=tk.DISABLED)

        tk.Button(dlg, text="Найти", command=do_get,
                  bg="#3b5998", fg="white", relief=tk.FLAT, padx=14).grid(
            row=1, column=0, columnspan=2, pady=6)


# ─────────────────────────────────────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()