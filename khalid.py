import sqlite3
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

# إعداد المظهر
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class Database:
    def __init__(self):
        self.db_name = "distribution.db"
        self.init_database()
    
    def init_database(self):
        """تهيئة قاعدة البيانات والجداول"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # جدول العملاء
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                created_date DATE,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # جدول أسعار المنتج
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                price_date DATE UNIQUE,
                price_per_kg REAL NOT NULL
            )
        ''')
        
        # جدول التوزيعات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS distributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                distribution_date DATE,
                quantity_kg REAL,
                price_per_kg REAL,
                total_amount REAL,
                paid_amount REAL,
                remaining_amount REAL,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        ''')
        
        # جدول المدفوعات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                payment_date DATE,
                amount REAL,
                payment_method TEXT,
                description TEXT,
                distribution_id INTEGER,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        ''')
        
        # إضافة مستخدم افتراضي
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        
        # إضافة المستخدم الافتراضي إذا لم يكن موجوداً
        cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", 
                      ('admin', 'admin123'))
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        """تنفيذ استعلام مع معاملات"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
    
    def fetch_all(self, query, params=()):
        """جلب جميع النتائج"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    def fetch_one(self, query, params=()):
        """جلب نتيجة واحدة"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result

class Auth:
    def __init__(self):
        self.db = Database()
        self.current_user = None
    
    def login(self, username, password):
        """تسجيل الدخول"""
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        user = self.db.fetch_one(query, (username, password))
        
        if user:
            self.current_user = user
            return True
        return False
    
    def change_password(self, new_password):
        """تغيير كلمة المرور"""
        if self.current_user:
            query = "UPDATE users SET password = ? WHERE id = ?"
            self.db.execute_query(query, (new_password, self.current_user[0]))
            return True
        return False

class ClientModel:
    def __init__(self):
        self.db = Database()
    
    def add_client(self, name, address, phone):
        """إضافة عميل جديد"""
        query = """INSERT INTO clients (name, address, phone, created_date) 
                   VALUES (?, ?, ?, ?)"""
        self.db.execute_query(query, (name, address, phone, datetime.now().date()))
    
    def get_all_clients(self):
        """جلب جميع العملاء"""
        query = "SELECT * FROM clients WHERE is_active = TRUE ORDER BY name"
        return self.db.fetch_all(query)
    
    def get_client_by_id(self, client_id):
        """جلب عميل بواسطة المعرف"""
        query = "SELECT * FROM clients WHERE id = ?"
        return self.db.fetch_one(query, (client_id,))
    
    def update_client(self, client_id, name, address, phone):
        """تحديث بيانات العميل"""
        query = """UPDATE clients SET name = ?, address = ?, phone = ? 
                   WHERE id = ?"""
        self.db.execute_query(query, (name, address, phone, client_id))
    
    def delete_client(self, client_id):
        """حذف عميل (تعطيل)"""
        query = "UPDATE clients SET is_active = FALSE WHERE id = ?"
        self.db.execute_query(query, (client_id,))
    
    def get_client_balance(self, client_id):
        """حساب رصيد العميل"""
        query = """
            SELECT 
                COALESCE(SUM(d.remaining_amount), 0) as total_balance
            FROM distributions d
            WHERE d.client_id = ? AND d.remaining_amount > 0
        """
        result = self.db.fetch_one(query, (client_id,))
        return result[0] if result else 0

class DistributionModel:
    def __init__(self):
        self.db = Database()
    
    def set_today_price(self, price):
        """تعيين سعر اليوم"""
        today = datetime.now().date()
        query = """INSERT OR REPLACE INTO product_prices (price_date, price_per_kg) 
                   VALUES (?, ?)"""
        self.db.execute_query(query, (today, price))
    
    def get_today_price(self):
        """جلب سعر اليوم"""
        today = datetime.now().date()
        query = "SELECT price_per_kg FROM product_prices WHERE price_date = ?"
        result = self.db.fetch_one(query, (today,))
        return result[0] if result else 0.0
    
    def add_distribution(self, client_id, quantity_kg, paid_amount=0):
        """إضافة توزيع جديد"""
        price_per_kg = self.get_today_price()
        total_amount = quantity_kg * price_per_kg
        remaining_amount = total_amount - paid_amount
        
        query = """INSERT INTO distributions 
                   (client_id, distribution_date, quantity_kg, price_per_kg, 
                    total_amount, paid_amount, remaining_amount) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)"""
        
        self.db.execute_query(query, (
            client_id, datetime.now().date(), quantity_kg, price_per_kg,
            total_amount, paid_amount, remaining_amount
        ))
    
    def get_daily_distributions(self, date=None):
        """جلب التوزيعات اليومية"""
        if date is None:
            date = datetime.now().date()
        
        query = """
            SELECT d.*, c.name as client_name 
            FROM distributions d
            JOIN clients c ON d.client_id = c.id
            WHERE d.distribution_date = ?
            ORDER BY d.id DESC
        """
        return self.db.fetch_all(query, (date,))
    
    def get_client_distributions(self, client_id):
        """جلب توزيعات عميل معين"""
        query = """
            SELECT * FROM distributions 
            WHERE client_id = ? 
            ORDER BY distribution_date DESC
        """
        return self.db.fetch_all(query, (client_id,))
    
    def get_total_distributions(self, start_date, end_date):
        """إجمالي التوزيعات في فترة محددة"""
        query = """
            SELECT 
                c.name,
                SUM(d.quantity_kg) as total_kg,
                SUM(d.total_amount) as total_amount,
                SUM(d.paid_amount) as total_paid,
                SUM(d.remaining_amount) as total_remaining
            FROM distributions d
            JOIN clients c ON d.client_id = c.id
            WHERE d.distribution_date BETWEEN ? AND ?
            GROUP BY c.id, c.name
        """
        return self.db.fetch_all(query, (start_date, end_date))

class PaymentModel:
    def __init__(self):
        self.db = Database()
    
    def add_payment(self, client_id, amount, payment_method, description, distribution_id=None):
        """إضافة دفعة جديدة"""
        query = """INSERT INTO payments 
                   (client_id, payment_date, amount, payment_method, description, distribution_id) 
                   VALUES (?, ?, ?, ?, ?, ?)"""
        
        self.db.execute_query(query, (
            client_id, datetime.now().date(), amount, 
            payment_method, description, distribution_id
        ))
        
        # تحديث الرصيد المتبقي في التوزيعات إذا كان الدفع مرتبطاً بتوزيع معين
        if distribution_id:
            self._update_distribution_balance(distribution_id, amount)
    
    def _update_distribution_balance(self, distribution_id, payment_amount):
        """تحديث رصيد التوزيع"""
        query = "SELECT remaining_amount FROM distributions WHERE id = ?"
        result = self.db.fetch_one(query, (distribution_id,))
        if result:
            current_balance = result[0]
            new_balance = max(0, current_balance - payment_amount)
            update_query = "UPDATE distributions SET remaining_amount = ? WHERE id = ?"
            self.db.execute_query(update_query, (new_balance, distribution_id))
    
    def get_client_payments(self, client_id):
        """جلب مدفوعات عميل معين"""
        query = """
            SELECT * FROM payments 
            WHERE client_id = ? 
            ORDER BY payment_date DESC
        """
        return self.db.fetch_all(query, (client_id,))
    
    def get_pending_payments(self):
        """جلب المدفوعات المستحقة"""
        query = """
            SELECT c.name, c.phone, SUM(d.remaining_amount) as pending_amount
            FROM clients c
            JOIN distributions d ON c.id = d.client_id
            WHERE d.remaining_amount > 0
            GROUP BY c.id, c.name
            HAVING SUM(d.remaining_amount) > 0
        """
        return self.db.fetch_all(query)

class Validators:
    @staticmethod
    def validate_phone(phone):
        """التحقق من صحة رقم الهاتف"""
        if not phone:
            return True
        import re
        pattern = r'^[\d\s\-\+\(\)]{8,}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_number(value):
        """التحقق من أن القيمة رقمية"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_required(value):
        """التحقق من أن الحقل مطلوب"""
        return bool(value and str(value).strip())

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.auth = Auth()
        self.setup_ui()
    
    def setup_ui(self):
        """إعداد واجهة تسجيل الدخول"""
        self.title("نظام إدارة التوزيع - تسجيل الدخول")
        self.geometry("400x300")
        self.resizable(False, False)
        
        # مركز النافذة
        self.center_window()
        
        # إطار رئيسي
        frame = ctk.CTkFrame(self)
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # عنوان
        title_label = ctk.CTkLabel(frame, text="تسجيل الدخول", font=("Arial", 20, "bold"))
        title_label.pack(pady=20)
        
        # حقل اسم المستخدم
        self.username_entry = ctk.CTkEntry(frame, placeholder_text="اسم المستخدم", width=250)
        self.username_entry.pack(pady=10)
        
        # حقل كلمة المرور
        self.password_entry = ctk.CTkEntry(frame, placeholder_text="كلمة المرور", 
                                         show="*", width=250)
        self.password_entry.pack(pady=10)
        
        # زر الدخول
        login_btn = ctk.CTkButton(frame, text="دخول", command=self.login, width=250)
        login_btn.pack(pady=20)
        
        # بيانات افتراضية للمساعدة
        help_label = ctk.CTkLabel(frame, text="بيانات الدخول: admin / admin123", 
                                font=("Arial", 12), text_color="gray")
        help_label.pack(pady=10)
        
        # ربط زر Enter بالدخول
        self.bind('<Return>', lambda event: self.login())
        self.username_entry.focus()
    
    def center_window(self):
        """توسيط النافذة على الشاشة"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def login(self):
        """معالجة تسجيل الدخول"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("خطأ", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return
        
        if self.auth.login(username, password):
            self.destroy()
            app = MainApp(self.auth)
            app.mainloop()
        else:
            messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")

class MainApp(ctk.CTk):
    def __init__(self, auth):
        super().__init__()
        
        self.auth = auth
        self.client_model = ClientModel()
        self.distribution_model = DistributionModel()
        self.payment_model = PaymentModel()
        
        self.setup_ui()
        self.show_dashboard()
    
    def setup_ui(self):
        """إعداد الواجهة الرئيسية"""
        self.title("نظام إدارة التوزيع")
        self.geometry("1000x700")
        
        # إطار رئيسي
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # شريط العنوان
        self.create_header()
        
        # الشريط الجانبي
        self.create_sidebar()
        
        # منطقة المحتوى
        self.create_content_area()
    
    def create_header(self):
        """إنشاء شريط العنوان"""
        header_frame = ctk.CTkFrame(self.main_frame, height=60)
        header_frame.pack(fill="x", padx=5, pady=5)
        header_frame.pack_propagate(False)
        
        title_label = ctk.CTkLabel(header_frame, text="نظام إدارة التوزيع", 
                                 font=("Arial", 18, "bold"))
        title_label.pack(side="right", padx=20, pady=10)
        
        date_label = ctk.CTkLabel(header_frame, text=datetime.now().strftime("%Y-%m-%d"),
                                font=("Arial", 14))
        date_label.pack(side="left", padx=20, pady=10)
    
    def create_sidebar(self):
        """إنشاء الشريط الجانبي"""
        sidebar_frame = ctk.CTkFrame(self.main_frame, width=200)
        sidebar_frame.pack(side="right", fill="y", padx=(5, 0))
        sidebar_frame.pack_propagate(False)
        
        # أزرار القائمة
        buttons = [
            ("لوحة التحكم", self.show_dashboard),
            ("إدارة العملاء", self.show_clients),
            ("التوزيع اليومي", self.show_distributions),
            ("إدارة المدفوعات", self.show_payments),
            ("التقارير", self.show_reports),
            ("إعدادات", self.show_settings)
        ]
        
        for text, command in buttons:
            btn = ctk.CTkButton(sidebar_frame, text=text, command=command,
                              font=("Arial", 14), height=40)
            btn.pack(fill="x", padx=10, pady=5)
    
    def create_content_area(self):
        """إنشاء منطقة المحتوى"""
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    def clear_content(self):
        """مسح محتوى المنطقة"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """عرض لوحة التحكم"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="لوحة التحكم", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # بطاقات الإحصائيات
        stats_frame = ctk.CTkFrame(self.content_frame)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        # إحصائيات سريعة
        clients_count = len(self.client_model.get_all_clients())
        today_distributions = self.distribution_model.get_daily_distributions()
        total_today = sum(dist[5] for dist in today_distributions)  # total_amount
        
        stats_data = [
            ("إجمالي العملاء", f"{clients_count}", "blue"),
            ("التوزيع اليومي", f"{total_today:,.2f} د.ج", "green"),
            ("سعر اليوم", f"{self.distribution_model.get_today_price():,.2f} د.ج/كغ", "orange")
        ]
        
        for i, (title, value, color) in enumerate(stats_data):
            stat_card = ctk.CTkFrame(stats_frame, width=200, height=100)
            stat_card.grid(row=0, column=i, padx=10, pady=10)
            stat_card.pack_propagate(False)
            
            title_label = ctk.CTkLabel(stat_card, text=title, font=("Arial", 14))
            title_label.pack(pady=(15, 5))
            
            value_label = ctk.CTkLabel(stat_card, text=value, font=("Arial", 18, "bold"))
            value_label.pack(pady=5)
    
    def show_clients(self):
        """عرض إدارة العملاء"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="إدارة العملاء", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # إطار الإضافة
        add_frame = ctk.CTkFrame(self.content_frame)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        # حقول الإدخال - محاذاة لليسار
        ctk.CTkLabel(add_frame, text="إضافة عميل جديد", font=("Arial", 14)).pack(pady=5)
        
        input_frame = ctk.CTkFrame(add_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        # الصف الأول
        name_frame = ctk.CTkFrame(input_frame)
        name_frame.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ctk.CTkEntry(name_frame, width=200, placeholder_text="أدخل اسم العميل")
        name_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(name_frame, text="الاسم:").pack(side="right")
        
        address_frame = ctk.CTkFrame(input_frame)
        address_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        address_entry = ctk.CTkEntry(address_frame, width=200, placeholder_text="أدخل العنوان")
        address_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(address_frame, text="العنوان:").pack(side="right")
        
        # الصف الثاني
        phone_frame = ctk.CTkFrame(input_frame)
        phone_frame.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        phone_entry = ctk.CTkEntry(phone_frame, width=200, placeholder_text="أدخل رقم الهاتف")
        phone_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(phone_frame, text="الهاتف:").pack(side="right")
        
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        add_btn = ctk.CTkButton(button_frame, text="إضافة عميل", command=lambda: self.add_client_handler(
            name_entry, address_entry, phone_entry, show_clients_list
        ))
        add_btn.pack(side="right", padx=(5, 0))
        
        # قائمة العملاء
        list_frame = ctk.CTkFrame(self.content_frame)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        def show_clients_list():
            # مسح القائمة الحالية
            for widget in list_frame.winfo_children():
                widget.destroy()
            
            clients = self.client_model.get_all_clients()
            
            if not clients:
                ctk.CTkLabel(list_frame, text="لا يوجد عملاء").pack(pady=20)
                return
            
            # إنشاء Treeview مع أزرار الإجراءات
            columns = ("ID", "الاسم", "العنوان", "الهاتف", "الرصيد", "الإجراءات")
            tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
            
            # عناوين الأعمدة
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            
            # إضافة البيانات
            for client in clients:
                balance = self.client_model.get_client_balance(client[0])
                tree.insert("", "end", values=(
                    client[0], client[1], client[2] or "", client[3] or "",
                    f"{balance:,.2f} د.ج", "تعديل / حذف"
                ))
            
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            
            # إطار أزرار الإجراءات
            action_frame = ctk.CTkFrame(list_frame)
            action_frame.pack(fill="x", padx=10, pady=5)
            
            def edit_client():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("تحذير", "يرجى اختيار عميل للتعديل")
                    return
                
                client_id = tree.item(selection[0])['values'][0]
                self.edit_client_dialog(client_id, show_clients_list)
            
            def delete_client():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("تحذير", "يرجى اختيار عميل للحذف")
                    return
                
                client_id = tree.item(selection[0])['values'][0]
                client_name = tree.item(selection[0])['values'][1]
                
                if messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف العميل {client_name}؟"):
                    self.client_model.delete_client(client_id)
                    messagebox.showinfo("نجاح", "تم حذف العميل بنجاح")
                    show_clients_list()
            
            ctk.CTkButton(action_frame, text="تعديل العميل المحدد", command=edit_client).pack(side="right", padx=5)
            ctk.CTkButton(action_frame, text="حذف العميل المحدد", command=delete_client, fg_color="red").pack(side="right", padx=5)
        
        show_clients_list()

    def add_client_handler(self, name_entry, address_entry, phone_entry, callback):
        """معالجة إضافة عميل جديد"""
        name = name_entry.get().strip()
        address = address_entry.get().strip()
        phone = phone_entry.get().strip()
        
        if not name:
            messagebox.showerror("خطأ", "يرجى إدخال اسم العميل")
            return
        
        self.client_model.add_client(name, address, phone)
        messagebox.showinfo("نجاح", "تم إضافة العميل بنجاح")
        name_entry.delete(0, tk.END)
        address_entry.delete(0, tk.END)
        phone_entry.delete(0, tk.END)
        callback()

    def edit_client_dialog(self, client_id, callback):
        """نافذة تعديل العميل"""
        client = self.client_model.get_client_by_id(client_id)
        if not client:
            messagebox.showerror("خطأ", "لم يتم العثور على العميل")
            return
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("تعديل العميل")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # مركز النافذة
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text="تعديل بيانات العميل", font=("Arial", 16, "bold")).pack(pady=10)
        
        # حقول الإدخال
        fields_frame = ctk.CTkFrame(dialog)
        fields_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # اسم العميل
        name_frame = ctk.CTkFrame(fields_frame)
        name_frame.pack(fill="x", padx=10, pady=5)
        name_entry = ctk.CTkEntry(name_frame, width=300)
        name_entry.insert(0, client[1])
        name_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(name_frame, text="الاسم:").pack(side="right")
        
        # العنوان
        address_frame = ctk.CTkFrame(fields_frame)
        address_frame.pack(fill="x", padx=10, pady=5)
        address_entry = ctk.CTkEntry(address_frame, width=300)
        address_entry.insert(0, client[2] or "")
        address_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(address_frame, text="العنوان:").pack(side="right")
        
        # الهاتف
        phone_frame = ctk.CTkFrame(fields_frame)
        phone_frame.pack(fill="x", padx=10, pady=5)
        phone_entry = ctk.CTkEntry(phone_frame, width=300)
        phone_entry.insert(0, client[3] or "")
        phone_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(phone_frame, text="الهاتف:").pack(side="right")
        
        def save_changes():
            new_name = name_entry.get().strip()
            new_address = address_entry.get().strip()
            new_phone = phone_entry.get().strip()
            
            if not new_name:
                messagebox.showerror("خطأ", "يرجى إدخال اسم العميل")
                return
            
            self.client_model.update_client(client_id, new_name, new_address, new_phone)
            messagebox.showinfo("نجاح", "تم تعديل بيانات العميل بنجاح")
            dialog.destroy()
            callback()
        
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(button_frame, text="حفظ التعديلات", command=save_changes).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="إلغاء", command=dialog.destroy).pack(side="left", padx=5)
    
    def show_distributions(self):
        """عرض التوزيع اليومي"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="التوزيع اليومي", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # إطار سعر اليوم
        price_frame = ctk.CTkFrame(self.content_frame)
        price_frame.pack(fill="x", padx=20, pady=10)
        
        current_price = self.distribution_model.get_today_price()
        price_label = ctk.CTkLabel(price_frame, text=f"سعر اليوم: {current_price:,.2f} د.ج/كغ", 
                    font=("Arial", 14))
        price_label.pack(side="left", padx=10, pady=5)
        
        ctk.CTkLabel(price_frame, text="تحديث السعر:").pack(side="left", padx=5)
        price_entry = ctk.CTkEntry(price_frame, width=100)
        price_entry.pack(side="left", padx=5)
        
        def update_price():
            new_price = price_entry.get().strip()
            if Validators.validate_number(new_price):
                self.distribution_model.set_today_price(float(new_price))
                messagebox.showinfo("نجاح", "تم تحديث السعر بنجاح")
                # تحديث عرض السعر
                current_price = self.distribution_model.get_today_price()
                price_label.configure(text=f"سعر اليوم: {current_price:,.2f} د.ج/كغ")
                price_entry.delete(0, tk.END)
                calculate_totals()  # إعادة حساب التوزيعات
            else:
                messagebox.showerror("خطأ", "يرجى إدخال سعر صحيح")
        
        ctk.CTkButton(price_frame, text="تحديث", command=update_price).pack(side="left", padx=5)
        
        # إطار التوزيع الجديد
        dist_frame = ctk.CTkFrame(self.content_frame)
        dist_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(dist_frame, text="تسجيل توزيع جديد", font=("Arial", 14)).pack(pady=5)
        
        input_frame = ctk.CTkFrame(dist_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        # الصف الأول
        client_frame = ctk.CTkFrame(input_frame)
        client_frame.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        clients = self.client_model.get_all_clients()
        client_names = [client[1] for client in clients]
        client_combo = ctk.CTkComboBox(client_frame, values=client_names, width=200)
        client_combo.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(client_frame, text="العميل:").pack(side="right")
        
        quantity_frame = ctk.CTkFrame(input_frame)
        quantity_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        quantity_entry = ctk.CTkEntry(quantity_frame, width=120, placeholder_text="الكمية بالكغ")
        quantity_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(quantity_frame, text="الكمية (كغ):").pack(side="right")
        
        # الصف الثاني
        paid_frame = ctk.CTkFrame(input_frame)
        paid_frame.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        paid_entry = ctk.CTkEntry(paid_frame, width=120, placeholder_text="0")
        paid_entry.insert(0, "0")
        paid_entry.pack(side="right", padx=(5, 0))
        ctk.CTkLabel(paid_frame, text="المدفوع فوراً:").pack(side="right")
        
        # عرض الحسابات التلقائية
        calc_frame = ctk.CTkFrame(input_frame)
        calc_frame.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        def calculate_totals():
            try:
                quantity = float(quantity_entry.get() or 0)
                price = self.distribution_model.get_today_price()
                paid = float(paid_entry.get() or 0)
                
                total = quantity * price
                remaining = total - paid
                
                calc_label.configure(
                    text=f"الإجمالي: {total:,.2f} | المتبقي: {remaining:,.2f}"
                )
            except:
                calc_label.configure(text="الإجمالي: 0.00 | المتبقي: 0.00")
        
        calc_label = ctk.CTkLabel(calc_frame, text="الإجمالي: 0.00 | المتبقي: 0.00",
                                font=("Arial", 12, "bold"))
        calc_label.pack(side="right", padx=(5, 0))
        
        # ربط الحقول بالحساب التلقائي
        quantity_entry.bind("<KeyRelease>", lambda e: calculate_totals())
        paid_entry.bind("<KeyRelease>", lambda e: calculate_totals())
        
        button_frame = ctk.CTkFrame(input_frame)
        button_frame.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        def add_distribution():
            client_name = client_combo.get()
            quantity = quantity_entry.get().strip()
            paid = paid_entry.get().strip()
            
            if not client_name or not quantity:
                messagebox.showerror("خطأ", "يرجى اختيار العميل وإدخال الكمية")
                return
            
            if not Validators.validate_number(quantity):
                messagebox.showerror("خطأ", "يرجى إدخال كمية صحيحة")
                return
            
            if not Validators.validate_number(paid):
                messagebox.showerror("خطأ", "يرجى إدخال مبلغ مدفوع صحيح")
                return
            
            # البحث عن معرف العميل
            client_id = None
            for client in clients:
                if client[1] == client_name:
                    client_id = client[0]
                    break
            
            if client_id:
                self.distribution_model.add_distribution(
                    client_id, float(quantity), float(paid)
                )
                messagebox.showinfo("نجاح", "تم تسجيل التوزيع بنجاح")
                quantity_entry.delete(0, tk.END)
                paid_entry.delete(0, tk.END)
                paid_entry.insert(0, "0")
                calculate_totals()
                show_daily_distributions()
            else:
                messagebox.showerror("خطأ", "لم يتم العثور على العميل")
        
        add_btn = ctk.CTkButton(button_frame, text="تسجيل التوزيع", command=add_distribution)
        add_btn.pack(side="right", padx=(5, 0))
        
        # قائمة التوزيعات اليومية
        list_frame = ctk.CTkFrame(self.content_frame)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        def show_daily_distributions():
            for widget in list_frame.winfo_children():
                widget.destroy()
            
            distributions = self.distribution_model.get_daily_distributions()
            
            if not distributions:
                ctk.CTkLabel(list_frame, text="لا توجد توزيعات لهذا اليوم").pack(pady=20)
                return
            
            columns = ("ID", "العميل", "الكمية (كغ)", "السعر", "الإجمالي", "المدفوع", "المتبقي", "التاريخ", "الإجراءات")
            tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=90)
            
            for dist in distributions:
                tree.insert("", "end", values=(
                    dist[0],  # ID
                    dist[8],  # client_name
                    f"{dist[3]:.2f}",
                    f"{dist[4]:,.2f}",
                    f"{dist[5]:,.2f}",
                    f"{dist[6]:,.2f}",
                    f"{dist[7]:,.2f}",
                    dist[2],
                    "تعديل / حذف"
                ))
            
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            
            # أزرار الإجراءات للتوزيعات
            action_frame = ctk.CTkFrame(list_frame)
            action_frame.pack(fill="x", padx=10, pady=5)
            
            def delete_distribution():
                selection = tree.selection()
                if not selection:
                    messagebox.showwarning("تحذير", "يرجى اختيار توزيع للحذف")
                    return
                
                dist_id = tree.item(selection[0])['values'][0]
                client_name = tree.item(selection[0])['values'][1]
                
                if messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف توزيع {client_name}؟"):
                    # سيتم إضافة دالة الحذف في النموذج لاحقاً
                    messagebox.showinfo("معلومة", "سيتم تطوير دالة الحذف في النسخة القادمة")
                    # show_daily_distributions()
            
            ctk.CTkButton(action_frame, text="حذف التوزيع المحدد", command=delete_distribution, 
                         fg_color="red").pack(side="right", padx=5)
        
        show_daily_distributions()
        calculate_totals()  # حساب أولي
    
    def show_payments(self):
        """عرض إدارة المدفوعات"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="إدارة المدفوعات", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # سيتم تطوير هذه الواجهة بشكل كامل
        ctk.CTkLabel(self.content_frame, text="واجهة إدارة المدفوعات - قيد التطوير",
                    font=("Arial", 14)).pack(pady=50)
    
    def show_reports(self):
        """عرض التقارير"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="التقارير", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # إطار اختيار الفترة
        period_frame = ctk.CTkFrame(self.content_frame)
        period_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(period_frame, text="من:").pack(side="left", padx=5)
        start_entry = ctk.CTkEntry(period_frame, width=100)
        start_entry.pack(side="left", padx=5)
        start_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        
        ctk.CTkLabel(period_frame, text="إلى:").pack(side="left", padx=5)
        end_entry = ctk.CTkEntry(period_frame, width=100)
        end_entry.pack(side="left", padx=5)
        end_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        def generate_report():
            start_date = start_entry.get().strip()
            end_date = end_entry.get().strip()
            
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("خطأ", "يرجى إدخال تاريخ صحيح (YYYY-MM-DD)")
                return
            
            results = self.distribution_model.get_total_distributions(start_date, end_date)
            show_report_results(results, start_date, end_date)
        
        ctk.CTkButton(period_frame, text="عرض التقرير", command=generate_report).pack(side="left", padx=10)
        
        # إطار النتائج
        self.results_frame = ctk.CTkFrame(self.content_frame)
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        def show_report_results(results, start_date, end_date):
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            
            if not results:
                ctk.CTkLabel(self.results_frame, text="لا توجد بيانات في الفترة المحددة").pack(pady=20)
                return
            
            title = ctk.CTkLabel(self.results_frame, 
                               text=f"تقرير التوزيعات من {start_date} إلى {end_date}",
                               font=("Arial", 14, "bold"))
            title.pack(pady=10)
            
            columns = ("العميل", "إجمالي الكمية (كغ)", "إجمالي المبلغ", "المدفوع", "المتبقي")
            tree = ttk.Treeview(self.results_frame, columns=columns, show="headings", height=15)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=150)
            
            total_kg = 0
            total_amount = 0
            total_paid = 0
            total_remaining = 0
            
            for row in results:
                tree.insert("", "end", values=(
                    row[0],  # client name
                    f"{row[1]:.2f}",
                    f"{row[2]:,.2f}",
                    f"{row[3]:,.2f}",
                    f"{row[4]:,.2f}"
                ))
                total_kg += row[1]
                total_amount += row[2]
                total_paid += row[3]
                total_remaining += row[4]
            
            # إجماليات
            tree.insert("", "end", values=(
                "الإجمالي",
                f"{total_kg:.2f}",
                f"{total_amount:,.2f}",
                f"{total_paid:,.2f}",
                f"{total_remaining:,.2f}"
            ), tags=("total",))
            
            tree.tag_configure("total", background="lightblue")
            
            tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # عرض تقرير افتراضي
        default_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        default_end = datetime.now().strftime("%Y-%m-%d")
        results = self.distribution_model.get_total_distributions(default_start, default_end)
        show_report_results(results, default_start, default_end)
    
    def show_settings(self):
        """عرض الإعدادات"""
        self.clear_content()
        
        title_label = ctk.CTkLabel(self.content_frame, text="الإعدادات", 
                                 font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # تغيير كلمة المرور
        pass_frame = ctk.CTkFrame(self.content_frame)
        pass_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(pass_frame, text="تغيير كلمة المرور", font=("Arial", 14)).pack(pady=5)
        
        input_frame = ctk.CTkFrame(pass_frame)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(input_frame, text="كلمة المرور الجديدة:").grid(row=0, column=0, padx=5, pady=5)
        new_pass_entry = ctk.CTkEntry(input_frame, show="*", width=200)
        new_pass_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="تأكيد كلمة المرور:").grid(row=1, column=0, padx=5, pady=5)
        confirm_pass_entry = ctk.CTkEntry(input_frame, show="*", width=200)
        confirm_pass_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def change_password():
            new_pass = new_pass_entry.get().strip()
            confirm_pass = confirm_pass_entry.get().strip()
            
            if not new_pass:
                messagebox.showerror("خطأ", "يرجى إدخال كلمة المرور الجديدة")
                return
            
            if new_pass != confirm_pass:
                messagebox.showerror("خطأ", "كلمتا المرور غير متطابقتين")
                return
            
            if self.auth.change_password(new_pass):
                messagebox.showinfo("نجاح", "تم تغيير كلمة المرور بنجاح")
                new_pass_entry.delete(0, tk.END)
                confirm_pass_entry.delete(0, tk.END)
            else:
                messagebox.showerror("خطأ", "فشل في تغيير كلمة المرور")
        
        ctk.CTkButton(input_frame, text="تغيير كلمة المرور", command=change_password).grid(row=1, column=2, padx=5, pady=5)

def main():
    """الدالة الرئيسية لتشغيل التطبيق"""
    login_window = LoginWindow()
    login_window.mainloop()

if __name__ == "__main__":
    main()
