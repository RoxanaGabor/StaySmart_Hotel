import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import hashlib
from datetime import datetime

from db import get_conn
from security import encrypt_text
from xml_tools import update_notes

BASE_DIR = Path(__file__).resolve().parents[1]


DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD_HASH = hashlib.sha256("password123".encode()).hexdigest()


COL_PRIMARY = "#38667E"
COL_SECONDARY = "#485861"
COL_BG = "#1F2023"
COL_SURFACE = "#1C425C"
COL_SURFACE_2 = "#24262B"
COL_OUTLINE = "#6E727A"
COL_TEXT = "#E6EAF0"
COL_MUTED = "#B7BCC3"


def center_window(win: tk.Tk, w: int, h: int):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


def month_to_pretty(value: str) -> str:
    """
    Converts 'YYYY-MM' or 'YYYY-MM-DD' to 'Month YYYY'.
    If parsing fails, returns original.
    """
    if not value:
        return value
    for fmt in ("%Y-%m", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%B %Y")
        except ValueError:
            pass
    return value

def date_to_ddmmyyyy(value: str) -> str:
    """Converts 'YYYY-MM-DD' to 'DD-MM-YYYY'. If parsing fails, returns original."""
    if not value:
        return value
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return value


class CardEntry(ttk.Entry):
    def __init__(self, master, **kwargs):
        self.var = tk.StringVar()
        super().__init__(master, textvariable=self.var, **kwargs)
        self._in_format = False
        self.bind("<KeyRelease>", self._on_keyrelease)

    def _on_keyrelease(self, _event):
        if self._in_format:
            return

        self._in_format = True
        try:
            raw = self.var.get()
            
            cursor_pos = self.index(tk.INSERT)

            digits_before_cursor = 0
            for i, ch in enumerate(raw[:cursor_pos]):
                if ch.isdigit():
                    digits_before_cursor += 1

            digits = "".join(ch for ch in raw if ch.isdigit())[:16]

            groups = [digits[i:i + 4] for i in range(0, len(digits), 4)]
            formatted = " ".join(groups)

            self.var.set(formatted)

            new_cursor = 0
            digits_seen = 0
            for i, ch in enumerate(formatted):
                if ch.isdigit():
                    digits_seen += 1
                if digits_seen >= digits_before_cursor:
                    new_cursor = i + 1
                    break
            else:
                new_cursor = len(formatted)

            self.icursor(new_cursor)
        finally:
            self._in_format = False

    def get_digits(self) -> str:
        return "".join(ch for ch in self.var.get() if ch.isdigit())


class Theme:
    @staticmethod
    def apply(root: tk.Tk):
        style = ttk.Style(root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        root.configure(bg=COL_BG)

        style.configure(".", background=COL_BG, foreground=COL_TEXT, font=("Arial", 12))

        style.configure("TFrame", background=COL_BG)
        style.configure("Card.TFrame", background=COL_SURFACE_2)
        style.configure("CardInner.TFrame", background=COL_SURFACE_2)

        style.configure("TLabel", background=COL_BG, foreground=COL_TEXT)
        style.configure("Title.TLabel", background=COL_BG, foreground=COL_TEXT, font=("Arial", 18, "bold"))
        style.configure("H2.TLabel", background=COL_SURFACE_2, foreground=COL_TEXT, font=("Arial", 13, "bold"))
        style.configure("Muted.TLabel", background=COL_SURFACE_2, foreground=COL_MUTED, font=("Arial", 10))

        style.configure(
            "TEntry",
            fieldbackground=COL_BG,
            background=COL_BG,
            foreground=COL_TEXT,
            bordercolor=COL_OUTLINE,
            lightcolor=COL_OUTLINE,
            darkcolor=COL_OUTLINE,
            insertcolor=COL_TEXT,
            padding=6,
        )

        style.configure(
            "TButton",
            background=COL_SURFACE,
            foreground=COL_TEXT,
            bordercolor=COL_OUTLINE,
            focusthickness=0,
            padding=(14, 10),
        )
        style.map(
            "TButton",
            background=[("active", COL_PRIMARY), ("pressed", COL_PRIMARY)],
            foreground=[("disabled", COL_MUTED)],
        )

        style.configure(
            "Accent.TButton",
            background=COL_PRIMARY,
            foreground=COL_TEXT,
            padding=(16, 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", COL_PRIMARY), ("pressed", COL_PRIMARY)],
        )

        style.configure("TNotebook", background=COL_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COL_SURFACE_2, foreground=COL_TEXT, padding=(14, 8))
        style.map(
            "TNotebook.Tab",
            background=[("selected", COL_PRIMARY)],
            foreground=[("selected", COL_TEXT)],
            padding=[("selected", (18, 10)), ("!selected", (14, 8))],
        )

        style.configure(
            "Treeview",
            background=COL_BG,
            fieldbackground=COL_BG,
            foreground=COL_TEXT,
            bordercolor=COL_OUTLINE,
            lightcolor=COL_OUTLINE,
            darkcolor=COL_OUTLINE,
            rowheight=28,
        )
        style.configure(
            "Treeview.Heading",
            background=COL_SURFACE_2,
            foreground=COL_TEXT,
            bordercolor=COL_OUTLINE,
            font=("Arial", 11, "bold"),
        )
        style.map("Treeview", background=[("selected", COL_PRIMARY)])
        style.map("Treeview.Heading", background=[("active", COL_SURFACE)])


class AuthWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        Theme.apply(self)
        self.title("StaySmart – Login")
        self.resizable(False, False)
        self.authenticated = False

        center_window(self, 620, 360)
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="StaySmart Hotel Management", style="Title.TLabel")
        title.pack(pady=(10, 24))

        form = ttk.Frame(outer)
        form.pack()

        ttk.Label(form, text="Username:").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 10))
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(form, textvariable=self.username_var, width=34)
        username_entry.grid(row=0, column=1, pady=(0, 10), ipady=3)
        username_entry.focus()

        ttk.Label(form, text="Password:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(0, 18))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(form, textvariable=self.password_var, width=34, show="•")
        password_entry.grid(row=1, column=1, pady=(0, 18), ipady=3)

        username_entry.bind("<Return>", lambda e: self.login())
        password_entry.bind("<Return>", lambda e: self.login())

        btns = ttk.Frame(outer)
        btns.pack(pady=(10, 0))
        ttk.Button(btns, text="Login", command=self.login, width=18).grid(row=0, column=0, padx=10)
        ttk.Button(btns, text="Exit", command=self.quit, width=18).grid(row=0, column=1, padx=10)

        info = ttk.Label(
            outer,
            foreground=COL_MUTED,
            background=COL_BG,
            font=("Arial", 10),
        )
        info.pack(pady=(18, 0))

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            messagebox.showwarning("Validation", "Please enter both username and password")
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if username == DEFAULT_USERNAME and password_hash == DEFAULT_PASSWORD_HASH:
            self.authenticated = True
            self.destroy()
        else:
            messagebox.showerror("Authentication Failed", "Invalid username or password")
            self.password_var.set("")

class StaySmartApp(tk.Tk):
    def __init__(self):
        super().__init__()
        Theme.apply(self)

        self.title("StaySmart – Hotel Management System")
        center_window(self, 1100, 700)

        self._build_ui()

    def _unfocus(self):
        try:
            self.focus_set()
        except Exception:
            pass

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.guests_tab = ttk.Frame(notebook)
        self.payments_tab = ttk.Frame(notebook)
        self.xml_tab = ttk.Frame(notebook)
        self.reports_tab = ttk.Frame(notebook)

        notebook.add(self.guests_tab, text="Guests")
        notebook.add(self.payments_tab, text="Payments (Encryption)")
        notebook.add(self.xml_tab, text="XML Preferences")
        notebook.add(self.reports_tab, text="Reports")

        self._build_guests_tab()
        self._build_payments_tab()
        self._build_xml_tab()
        self._build_reports_tab()

    # =========================
    # Guests
    # =========================
    def _build_guests_tab(self):
        frm = ttk.Frame(self.guests_tab, padding=12)
        frm.pack(fill="both", expand=True)

        left = ttk.Frame(frm)
        left.pack(side="left", fill="y", padx=(0, 14))

        ttk.Label(left, text="First name").pack(anchor="w")
        self.g_first = ttk.Entry(left, width=28)
        self.g_first.pack(pady=6)

        ttk.Label(left, text="Last name").pack(anchor="w")
        self.g_last = ttk.Entry(left, width=28)
        self.g_last.pack(pady=6)

        ttk.Label(left, text="Email").pack(anchor="w")
        self.g_email = ttk.Entry(left, width=28)
        self.g_email.pack(pady=6)

        ttk.Label(left, text="Phone").pack(anchor="w")
        self.g_phone = ttk.Entry(left, width=28)
        self.g_phone.pack(pady=6)

        ttk.Button(left, text="Add guest", command=self.add_guest).pack(fill="x", pady=(10, 6))
        ttk.Button(left, text="Update selected", command=self.update_guest).pack(fill="x", pady=6)
        ttk.Button(left, text="Delete selected", command=self.delete_guest).pack(fill="x", pady=6)

        right = ttk.Frame(frm)
        right.pack(side="left", fill="both", expand=True)

        cols = ("guest_id", "first_name", "last_name", "email", "phone")
        self.g_tree = ttk.Treeview(right, columns=cols, show="headings")
        for c in cols:
            self.g_tree.heading(c, text=c)
            self.g_tree.column(c, width=130 if c != "email" else 280, anchor="center")
        self.g_tree.column("email", anchor="w")
        self.g_tree.pack(fill="both", expand=True)

        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=8)
        ttk.Button(bottom, text="Refresh", command=self.load_guests).pack(side="right")

        self.g_tree.bind("<<TreeviewSelect>>", self._on_guest_select)
        self.load_guests()

    def _clear_guest_fields(self):
        for e in (self.g_first, self.g_last, self.g_email, self.g_phone):
            e.delete(0, tk.END)

    def load_guests(self):
        self.g_tree.delete(*self.g_tree.get_children())
        with get_conn() as con:
            rows = con.execute(
                "SELECT guest_id, first_name, last_name, email, phone FROM guests"
            ).fetchall()
        for r in rows:
            self.g_tree.insert("", "end", values=r)

    def _selected_guest_id(self):
        sel = self.g_tree.selection()
        if not sel:
            return None
        return int(self.g_tree.item(sel[0])["values"][0])

    def _on_guest_select(self, _):
        gid = self._selected_guest_id()
        if not gid:
            return
        with get_conn() as con:
            row = con.execute(
                "SELECT first_name, last_name, email, phone FROM guests WHERE guest_id = ?",
                (gid,)
            ).fetchone()
        if not row:
            return
        self.g_first.delete(0, tk.END); self.g_first.insert(0, row[0] or "")
        self.g_last.delete(0, tk.END); self.g_last.insert(0, row[1] or "")
        self.g_email.delete(0, tk.END); self.g_email.insert(0, row[2] or "")
        self.g_phone.delete(0, tk.END); self.g_phone.insert(0, row[3] or "")

    def add_guest(self):
        if not self.g_first.get().strip() or not self.g_last.get().strip() or not self.g_email.get().strip():
            messagebox.showwarning("Validation", "First name, last name and email are required")
            return
        with get_conn() as con:
            con.execute(
                "INSERT INTO guests(first_name,last_name,email,phone) VALUES (?,?,?,?)",
                (self.g_first.get().strip(), self.g_last.get().strip(), self.g_email.get().strip(), self.g_phone.get().strip())
            )
        self.load_guests()
        self._clear_guest_fields()

    def update_guest(self):
        gid = self._selected_guest_id()
        if not gid:
            messagebox.showwarning("Select a guest", "Pick a guest from the table first.")
            return
        with get_conn() as con:
            con.execute(
                "UPDATE guests SET first_name=?, last_name=?, email=?, phone=? WHERE guest_id=?",
                (self.g_first.get().strip(), self.g_last.get().strip(), self.g_email.get().strip(), self.g_phone.get().strip(), gid)
            )
        self.load_guests()
        self._clear_guest_fields()

    def delete_guest(self):
        gid = self._selected_guest_id()
        if not gid:
            messagebox.showwarning("Select a guest", "Pick a guest from the table first.")
            return
        if messagebox.askyesno("Confirm", "Delete selected guest?"):
            with get_conn() as con:
                con.execute("DELETE FROM guests WHERE guest_id=?", (gid,))
            self.load_guests()
            self._clear_guest_fields()

    # =========================
    # Payments
    # =========================
    def _build_payments_tab(self):
        outer = ttk.Frame(self.payments_tab, padding=12)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.place(relx=0.5, rely=0.42, anchor="center")

        ttk.Label(card, text="Store payment card (encrypted)", style="H2.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(card, text="Booking ID", background=COL_SURFACE_2).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.p_booking = ttk.Entry(card, width=30)
        self.p_booking.grid(row=1, column=1, pady=6, ipady=3)

        ttk.Label(card, text="Card number (we store encrypted last 4 only)", background=COL_SURFACE_2).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        self.p_card = CardEntry(card, width=30)
        self.p_card.grid(row=2, column=1, pady=6, ipady=3)

        btns = ttk.Frame(card, style="CardInner.TFrame")
        btns.grid(row=3, column=0, columnspan=2, pady=(14, 6))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        ttk.Button(btns, text="Save encrypted last 4", command=self.save_encrypted_card, width=22).grid(row=0, column=0, padx=8)
        ttk.Button(btns, text="Clear", command=self.clear_payment_fields, width=14).grid(row=0, column=1, padx=8)

        ttk.Label(
            card,
            style="Muted.TLabel"
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def clear_payment_fields(self):
        self.p_booking.delete(0, tk.END)
        self.p_card.var.set("")

    def save_encrypted_card(self):
        booking = self.p_booking.get().strip()
        digits = self.p_card.get_digits()

        if not booking:
            messagebox.showwarning("Validation", "Booking ID is required.")
            return

        if len(digits) != 16:
            messagebox.showwarning("Validation", "Card number must be exactly 16 digits.")
            return

        last4 = digits[-4:]
        encrypted = encrypt_text(last4)

        with get_conn() as con:
            cur = con.execute(
                "UPDATE payments SET card_last4_encrypted=? WHERE booking_id=?",
                (encrypted, booking)
            )
            if cur.rowcount == 0:
                messagebox.showerror("Not found", "No payment record found for that Booking ID.")
                return

        messagebox.showinfo("Saved", "Encrypted last 4 digits stored successfully.")
        self.clear_payment_fields()

    # =========================
    # XML
    # =========================
    def _build_xml_tab(self):
        outer = ttk.Frame(self.xml_tab, padding=12)
        outer.pack(fill="both", expand=True)

        card = ttk.Frame(outer, style="Card.TFrame", padding=18)
        card.place(relx=0.5, rely=0.42, anchor="center")

        ttk.Label(card, text="Update booking XML notes", style="H2.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(card, text="Booking ID", background=COL_SURFACE_2).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.x_booking = ttk.Entry(card, width=34)
        self.x_booking.grid(row=1, column=1, pady=6, ipady=3)

        ttk.Label(card, text="New notes", background=COL_SURFACE_2).grid(row=2, column=0, sticky="nw", padx=(0, 10), pady=6)

        self.x_notes = tk.Text(card, width=34, height=5, bg=COL_BG, fg=COL_TEXT, insertbackground=COL_TEXT,
                               highlightbackground=COL_OUTLINE, highlightcolor=COL_PRIMARY, relief="flat", padx=8, pady=8)
        self.x_notes.grid(row=2, column=1, pady=6)

        btns = ttk.Frame(card, style="CardInner.TFrame")
        btns.grid(row=3, column=0, columnspan=2, pady=(14, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        ttk.Button(btns, text="Update XML notes", command=self.update_xml_notes, width=18).grid(row=0, column=0, padx=8)
        ttk.Button(btns, text="Clear", command=self.clear_xml_fields, width=14).grid(row=0, column=1, padx=8)

    def clear_xml_fields(self):
        self.x_booking.delete(0, tk.END)
        self.x_notes.delete("1.0", tk.END)

    def update_xml_notes(self):
        booking = self.x_booking.get().strip()
        notes = self.x_notes.get("1.0", tk.END).strip()

        if not booking:
            messagebox.showwarning("Validation", "Booking ID is required.")
            return

        if not notes:
            messagebox.showwarning("Validation", "Notes cannot be empty.")
            return

        with get_conn() as con:
            row = con.execute(
                "SELECT preferences_xml FROM bookings WHERE booking_id=?",
                (booking,)
            ).fetchone()
            if not row:
                messagebox.showerror("Not found", "No booking found for that Booking ID.")
                return

            existing_xml = row[0] or ""
            updated_xml = update_notes(existing_xml, notes)

            con.execute(
                "UPDATE bookings SET preferences_xml=? WHERE booking_id=?",
                (updated_xml, booking)
            )

        messagebox.showinfo("Updated", "Booking XML notes updated successfully.")
        self.clear_xml_fields()

    # =========================
    # Reports (read-only views)
    # =========================
    def _build_reports_tab(self):
        frm = ttk.Frame(self.reports_tab, padding=12)
        frm.pack(fill="both", expand=True)

        top = ttk.Frame(frm)
        top.pack(fill="x")

        ttk.Label(top, text="Reports (read-only)").pack(side="left")

        ttk.Button(top, text="Revenue by month", command=self.load_revenue_by_month).pack(side="right", padx=(8, 0))
        ttk.Button(top, text="Upcoming Check Ins", command=self.load_upcoming_checkins).pack(side="right")

        self.report_title = ttk.Label(frm, text="", font=("Arial", 14, "bold"))
        self.report_title.pack(anchor="w", pady=(12, 6))

        self.report_summary = ttk.Label(frm, text="", foreground=COL_MUTED)
        self.report_summary.pack(anchor="w", pady=(0, 8))

        self.report_tree = ttk.Treeview(frm, show="headings")
        self.report_tree.pack(fill="both", expand=True)

        self.report_tree.tag_configure("odd", background=COL_BG)
        self.report_tree.tag_configure("even", background="#23252A")

        self.load_upcoming_checkins()

    def _set_report_columns(self, cols):
        self.report_tree.delete(*self.report_tree.get_children())
        self.report_tree["columns"] = cols

        for c in cols:
            self.report_tree.heading(c, text=c)
            self.report_tree.column(c, width=170, anchor="center")

        if "guest_email" in cols:
            self.report_tree.column("guest_email", anchor="w", width=260)
        if "guest_name" in cols:
            self.report_tree.column("guest_name", anchor="w", width=220)

    def _insert_striped_rows(self, rows):
        self.report_tree.delete(*self.report_tree.get_children())
        for i, r in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self.report_tree.insert("", "end", values=r, tags=(tag,))

    def load_upcoming_checkins(self):
        self.report_title.config(text="Upcoming Check Ins")
        self.report_summary.config(text="")

        cols = ("Booking Id", "Check In", "Check Out", "Status", "Room Number", "Guest Name", "Guest Email")
        self._set_report_columns(cols)

        try:
            with get_conn() as con:
                rows = con.execute(
                    "SELECT booking_id, check_in, check_out, status, room_number, guest_name, guest_email "
                    "FROM vw_upcoming_checkins;"
                ).fetchall()

            formatted = []
            for booking_id, check_in, check_out, status, room_number, guest_name, guest_email in rows:
                formatted.append((
                    booking_id,
                    date_to_ddmmyyyy(check_in),
                    date_to_ddmmyyyy(check_out),
                    status,
                    room_number,
                    guest_name,
                    guest_email
                ))

            self._insert_striped_rows(formatted)

        except sqlite3.Error as e:
            messagebox.showerror("Report error", f"Could not load upcoming check-ins.\n\n{e}")

    def load_revenue_by_month(self):
        self.report_title.config(text="Revenue by month")

        cols = ("Revenue Month", "Payment Count", "Total Revenue")
        self._set_report_columns(cols)

        try:
            with get_conn() as con:
                rows = con.execute(
                    "SELECT revenue_month, payment_count, total_revenue FROM vw_revenue_by_month;"
                ).fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Report error", f"Could not load revenue report.\n\n{e}")
            return

        pretty_rows = []
        total_revenue = 0.0
        total_payments = 0
        periods = []

        for (month_raw, pay_count, revenue) in rows:
            pretty_month = month_to_pretty(month_raw)
            pretty_rows.append((pretty_month, pay_count, revenue))

            try:
                total_revenue += float(revenue)
            except Exception:
                pass

            try:
                total_payments += int(pay_count)
            except Exception:
                pass

            periods.append(pretty_month)

        self.report_summary.config(
            text=f"Total revenue: £{total_revenue:.2f}   |   Payments: {total_payments}   |   Period(s): {', '.join(periods) if periods else 'N/A'}"
        )

        self._insert_striped_rows(pretty_rows)


if __name__ == "__main__":
    auth = AuthWindow()
    auth.mainloop()

    if auth.authenticated:
        app = StaySmartApp()
        app.mainloop()
