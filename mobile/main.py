import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
import requests

API_BASE = "http://127.0.0.1:8000"

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.email_input = TextInput(hint_text='Email', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.password_input = TextInput(hint_text='Password', password=True, multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        login_btn = Button(text='Login', size_hint=(None, None), width=250, height=40, pos_hint={'center_x': 0.5})
        login_btn.bind(on_press=self.login)
        self.message_label = Label(text='')
        layout.add_widget(self.email_input)
        layout.add_widget(self.password_input)
        layout.add_widget(login_btn)
        layout.add_widget(self.message_label)
        self.add_widget(layout)

    def login(self, instance):
        email = self.email_input.text
        password = self.password_input.text
        try:
            response = requests.post(f"{API_BASE}/token", data={"username": email, "password": password})
            if response.status_code == 200:
                resp_json = response.json()
                token = resp_json["access_token"]
                user_email = resp_json.get("email", email)
                self.manager.current = "main"
                main_screen = self.manager.get_screen("main")
                main_screen.set_user_email(user_email)
                main_screen.set_token(token)
            else:
                reg_response = requests.post(f"{API_BASE}/register", json={"email": email, "password": password})
                if reg_response.status_code == 200:
                    resp_json = reg_response.json()
                    token = resp_json["access_token"]
                    user_email = resp_json.get("email", email)
                    self.manager.current = "main"
                    main_screen = self.manager.get_screen("main")
                    main_screen.set_user_email(user_email)
                    main_screen.set_token(token)
                    self.message_label.text = "Account created and logged in."
                else:
                    try:
                        error_msg = reg_response.json().get("detail", "Login failed. Check credentials.")
                    except Exception:
                        error_msg = "Login failed. Check credentials."
                    self.message_label.text = error_msg
        except Exception as e:
            self.message_label.text = f"Error: {e}"

class MainScreen(Screen):
    def set_user_email(self, email):
        self.user_email = email
        print(f"DEBUG: Set user_email to {email}")
    def show_vitals(self):
        self.vitals_list.clear_widgets()
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/vitals", headers=headers)
            if response.status_code == 200:
                vitals = response.json()
                vitals_sorted = sorted(vitals, key=lambda v: v.get('record_time', ''), reverse=True)
                for vital in vitals_sorted[:5]:
                    bp = vital.get('bp', vital.get('value', ''))
                    hr = vital.get('hr', '')
                    temp = vital.get('temp', '')
                    record_time = vital.get('record_time', '')
                    vital_text = f"BP: {bp} | HR: {hr} | Temp: {temp} | Time: {record_time}"
                    vital_label = Label(text=vital_text, size_hint_y=None, height=40)
                    self.vitals_list.add_widget(vital_label)
                self.show_more_vitals_btn.opacity = 1 if len(vitals) > 5 else 0
            else:
                self.vitals_list.add_widget(Label(text="Failed to load vitals", size_hint_y=None, height=30))
        except Exception as e:
            self.vitals_list.add_widget(Label(text=f"Error: {e}", size_hint_y=None, height=30))
    def show_all_vitals(self, instance):
        self.clear_widgets()
        temp_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        # Center the vitals_list horizontally
        vitals_list_box = BoxLayout(orientation='horizontal', size_hint=(1, None))
        vitals_list_box.add_widget(Label(size_hint_x=0.25))
        vitals_list = GridLayout(cols=1, size_hint=(0.5, None), width=250, padding=[0,10,0,0], spacing=5)
        vitals_list.bind(minimum_height=vitals_list.setter('height'))
        # Add the title label as the first item in the grid
        title_label = Label(text='All Vitals', font_size=18, size_hint=(None, None), width=250, height=50, halign='center', valign='middle')
        title_label.bind(size=title_label.setter('text_size'))
        vitals_list.add_widget(title_label)
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/vitals", headers=headers)
            if response.status_code == 200:
                vitals = response.json()
                # Sort vitals by record_time descending
                vitals_sorted = sorted(vitals, key=lambda v: v.get('record_time', ''), reverse=True)
                for vital in vitals_sorted:
                    bp = vital.get('bp', vital.get('value', ''))
                    hr = vital.get('hr', '')
                    temp = vital.get('temp', '')
                    record_time = vital.get('record_time', '')
                    vital_text = f"BP: {bp} | HR: {hr} | Temp: {temp} | Time: {record_time}"
                    vital_label = Label(text=vital_text, size_hint=(None, None), width=250, height=30, halign='center', valign='middle')
                    vital_label.bind(size=vital_label.setter('text_size'))
                    vitals_list.add_widget(vital_label)
            else:
                vitals_list.add_widget(Label(text="Failed to load vitals", size_hint=(None, None), width=250, height=30, halign='center', valign='middle'))
        except Exception as e:
            vitals_list.add_widget(Label(text=f"Error: {e}", size_hint=(None, None), width=250, height=30, halign='center', valign='middle'))
        vitals_list_box.add_widget(vitals_list)
        vitals_list_box.add_widget(Label(size_hint_x=0.25))
        temp_layout.add_widget(vitals_list_box)
        home_btn = Button(text='Home', size_hint=(None, None), size=(120, 40), pos_hint={'center_x': 0.5})
        home_btn.bind(on_press=self.go_home)
        box = BoxLayout(size_hint=(1, None), height=60)
        box.add_widget(Label())
        box.add_widget(home_btn)
        box.add_widget(Label())
        temp_layout.add_widget(box)
        self.add_widget(temp_layout)
    def open_add_med(self, instance):
        self.manager.current = "add_med"
        self.manager.get_screen("add_med").set_token(self.token)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.token = None
        print("DEBUG: MainScreen __init__ called")
        layout = BoxLayout(orientation='vertical', padding=[0,10,10,10], spacing=5)
        welcome_label = Label(text='Welcome to MedBuddy!', font_size=20, size_hint=(1, None), height=30)
        reminder_label = Label(text='', font_size=40, size_hint=(1, None), height=60)
        try:
            reminder_label.bold = True
        except Exception:
            pass
        med_label = Label(text='Medications:', size_hint=(1, None), height=25)
        med_list = GridLayout(cols=1, size_hint_y=None)
        med_list.bind(minimum_height=med_list.setter('height'))
        show_more_med_btn = Button(text='Show More', size_hint=(None, None), size=(100, 30), pos_hint={'center_x': 0.5})
        show_more_med_btn.bind(on_press=self.show_all_meds)
        add_med_btn = Button(text='Add Medication', size_hint=(1, None), height=40)
        add_med_btn.bind(on_press=self.open_add_med)
        vitals_label = Label(text='Vitals:', size_hint=(1, None), height=25)
        vitals_list = GridLayout(cols=1, size_hint_y=None)
        vitals_list.bind(minimum_height=vitals_list.setter('height'))
        show_more_vitals_btn = Button(text='Show More', size_hint=(None, None), size=(120, 40), pos_hint={'center_x': 0.5})
        show_more_vitals_btn.bind(on_press=self.show_all_vitals)
        add_vitals_btn = Button(text='Add Vitals', size_hint=(1, None), height=40)
        add_vitals_btn.bind(on_press=self.open_add_vitals)
        logout_btn = Button(text='Logout', size_hint=(1, None), height=40)
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(welcome_label)
        layout.add_widget(reminder_label)
        layout.add_widget(med_label)
        layout.add_widget(med_list)
        layout.add_widget(show_more_med_btn)
        layout.add_widget(vitals_label)
        layout.add_widget(vitals_list)
        layout.add_widget(show_more_vitals_btn)
        from kivy.uix.widget import Widget
        layout.add_widget(Widget(size_hint_y=1))
        button_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, padding=10, spacing=10)
        button_box.add_widget(add_med_btn)
        button_box.add_widget(add_vitals_btn)
        button_box.add_widget(logout_btn)
        layout.add_widget(button_box)
        self.add_widget(layout)
        self.layout = layout
        self.welcome_label = welcome_label
        self.reminder_label = reminder_label
        self.med_label = med_label
        self.med_list = med_list
        self.show_more_med_btn = show_more_med_btn
        self.add_med_btn = add_med_btn
        self.vitals_label = vitals_label
        self.vitals_list = vitals_list
        self.show_more_vitals_btn = show_more_vitals_btn
        self.add_vitals_btn = add_vitals_btn
        self.logout_btn = logout_btn
        self.med_list.bind(minimum_height=self.med_list.setter('height'))
        self.show_more_med_btn = Button(text='Show More', size_hint=(None, None), size=(100, 30), pos_hint={'center_x': 0.5})
        self.show_more_med_btn.bind(on_press=self.show_all_meds)

        self.add_med_btn = Button(text='Add Medication', size_hint=(1, None), height=40)
        self.add_med_btn.bind(on_press=self.open_add_med)

        self.vitals_label = Label(text='Vitals:', size_hint=(1, None), height=25)
        self.vitals_list = GridLayout(cols=1, size_hint_y=None)
        self.vitals_list.bind(minimum_height=self.vitals_list.setter('height'))
        self.show_more_vitals_btn = Button(text='Show More', size_hint=(None, None), size=(120, 40), pos_hint={'center_x': 0.5})
        self.show_more_vitals_btn.bind(on_press=self.show_all_vitals)

        self.add_vitals_btn = Button(text='Add Vitals', size_hint=(1, None), height=40)
        self.add_vitals_btn.bind(on_press=self.open_add_vitals)

        self.logout_btn = Button(text='Logout', size_hint=(1, None), height=40)
        self.logout_btn.bind(on_press=self.logout)

    # ...existing code...

    def set_token(self, token):
        self.token = token
        print(f"DEBUG: set_token called with token={token}")
        self.go_home()

    def show_medication(self):
        self.med_list.clear_widgets()
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/meds", headers=headers)
            if response.status_code == 200:
                meds = response.json()
                for med in meds[:5]:
                    name = med.get('name', '')
                    dose = med.get('dose', '')
                    times = med.get('times', [])
                    schedule = ", ".join(times) if isinstance(times, list) else str(times)
                    start_date = med.get('start_date', '')
                    end_date = med.get('end_date', '')
                    med_text = f"Name: {name} | Dose: {dose} | Schedule: {schedule} | Start: {start_date} | End: {end_date}"
                    med_label = Label(text=med_text, size_hint_y=None, height=40)
                    self.med_list.add_widget(med_label)
                self.show_more_med_btn.opacity = 1 if len(meds) > 5 else 0
            else:
                self.med_list.add_widget(Label(text="Failed to load medications", size_hint_y=None, height=30))
        except Exception as e:
            self.med_list.add_widget(Label(text=f"Error: {e}", size_hint_y=None, height=30))
        
    def show_all_meds(self, instance):
        self.clear_widgets()
        temp_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        # Center the med_list horizontally
        med_list_box = BoxLayout(orientation='horizontal', size_hint=(1, None))
        med_list_box.add_widget(Label(size_hint_x=0.25))
        med_list = GridLayout(cols=1, size_hint=(0.5, None), width=250, padding=[0,10,0,0], spacing=5)
        med_list.bind(minimum_height=med_list.setter('height'))
    # ...existing code...
        # Add the title label as the first item in the grid
        title_label = Label(text='All Medications', font_size=18, size_hint=(None, None), width=250, height=50, halign='center', valign='middle')
        title_label.bind(size=title_label.setter('text_size'))
        med_list.add_widget(title_label)
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/meds", headers=headers)
            if response.status_code == 200:
                meds = response.json()
                for med in meds:
                    name = med.get('name', '')
                    dose = med.get('dose', '')
                    times = med.get('times', [])
                    schedule = ", ".join(times) if isinstance(times, list) else str(times)
                    start_date = med.get('start_date', '')
                    end_date = med.get('end_date', '')
                    med_text = f"Name: {name} | Dose: {dose} | Schedule: {schedule} | Start: {start_date} | End: {end_date}"
                    med_label = Label(text=med_text, size_hint=(None, None), width=250, height=30, halign='center', valign='middle')
                    med_label.bind(size=med_label.setter('text_size'))
                    med_list.add_widget(med_label)
            else:
                med_list.add_widget(Label(text="Failed to load medications", size_hint=(None, None), width=250, height=30, halign='center', valign='middle'))
        except Exception as e:
            med_list.add_widget(Label(text=f"Error: {e}", size_hint=(None, None), width=250, height=30, halign='center', valign='middle'))
        med_list_box.add_widget(med_list)
        med_list_box.add_widget(Label(size_hint_x=0.25))
        temp_layout.add_widget(med_list_box)
        home_btn = Button(text='Home', size_hint=(None, None), size=(120, 40), pos_hint={'center_x': 0.5})
        home_btn.bind(on_press=self.go_home)
        box = BoxLayout(size_hint=(1, None), height=60)
        box.add_widget(Label())
        box.add_widget(home_btn)
        box.add_widget(Label())
        temp_layout.add_widget(box)
        self.add_widget(temp_layout)

    def show_reminder(self):
        if not hasattr(self, 'reminder_label'):
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/reminders", headers=headers)
            if response.status_code == 200:
                reminders = response.json()
                if reminders:
                    details = []
                    for r in reminders:
                        name = r.get('name', 'Unknown')
                        dose = r.get('dose', '')
                        sched = r.get('scheduled_for', '')
                        details.append(f"{name} ({dose}) at {sched}")
                    self.reminder_label.text = f"Reminders: {len(reminders)} medicines delayed!\n" + "\n".join(details)
                else:
                    self.reminder_label.text = "No reminders right now."
            else:
                self.reminder_label.text = "Failed to load reminders."
        except Exception as e:
            self.reminder_label.text = f"Error: {e}"

    def go_home(self, instance=None):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=[0,10,10,10], spacing=5)
        # Centered welcome label and user email label
        welcome_label = Label(text='Welcome to MedBuddy!', font_size=20, size_hint=(1, None), height=40, halign='center', valign='middle')
        welcome_label.bind(size=welcome_label.setter('text_size'))
        layout.add_widget(welcome_label)
        if hasattr(self, 'user_email') and self.user_email:
            user_label = Label(text=f'Welcome, {self.user_email}!', font_size=18, size_hint=(1, None), height=30, halign='center', valign='middle')
            user_label.bind(size=user_label.setter('text_size'))
            layout.add_widget(user_label)

        # Reminder label (copied logic from show_reminder)
            reminder_label = Label(text='', font_size=30, size_hint=(1, None), height=60)
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.get(f"{API_BASE}/reminders", headers=headers)
            if response.status_code == 200:
                reminders = response.json()
                if reminders:
                    details = []
                    for r in reminders:
                        name = r.get('name', 'Unknown')
                        dose = r.get('dose', '')
                        sched = r.get('scheduled_for', '')
                        details.append(f"{name} ({dose}) at {sched}")
                    reminder_label.text = f"Reminders: {len(reminders)} medicines delayed!\n" + "\n".join(details)
                else:
                    reminder_label.text = "No reminders right now."
            else:
                reminder_label.text = "Failed to load reminders."
        except Exception as e:
            reminder_label.text = f"Error: {e}"
        layout.add_widget(reminder_label)

        med_label = Label(text='Medications:', size_hint=(1, None), height=25)
        med_list = GridLayout(cols=1, size_hint_y=None)
        med_list.bind(minimum_height=med_list.setter('height'))
        show_more_med_btn = Button(text='Show More', size_hint=(None, None), size=(100, 30), pos_hint={'center_x': 0.5})
        show_more_med_btn.bind(on_press=self.show_all_meds)
        add_med_btn = Button(text='Add Medication', size_hint=(1, None), height=40)
        add_med_btn.bind(on_press=self.open_add_med)
        vitals_label = Label(text='Vitals:', size_hint=(1, None), height=25)
        vitals_list = GridLayout(cols=1, size_hint_y=None)
        vitals_list.bind(minimum_height=vitals_list.setter('height'))
        show_more_vitals_btn = Button(text='Show More', size_hint=(None, None), size=(120, 40), pos_hint={'center_x': 0.5})
        show_more_vitals_btn.bind(on_press=self.show_all_vitals)
        add_vitals_btn = Button(text='Add Vitals', size_hint=(1, None), height=40)
        add_vitals_btn.bind(on_press=self.open_add_vitals)
        logout_btn = Button(text='Logout', size_hint=(1, None), height=40)
        logout_btn.bind(on_press=self.logout)
        layout.add_widget(med_label)
        layout.add_widget(med_list)
        layout.add_widget(show_more_med_btn)
        layout.add_widget(vitals_label)
        layout.add_widget(vitals_list)
        layout.add_widget(show_more_vitals_btn)
        from kivy.uix.widget import Widget
        layout.add_widget(Widget(size_hint_y=1))
        button_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, padding=10, spacing=10)
        button_box.add_widget(add_med_btn)
        button_box.add_widget(add_vitals_btn)
        button_box.add_widget(logout_btn)
        layout.add_widget(button_box)
        self.add_widget(layout)
        self.layout = layout
        self.welcome_label = welcome_label
        self.reminder_label = reminder_label
        self.med_label = med_label
        self.med_list = med_list
        self.show_more_med_btn = show_more_med_btn
        self.add_med_btn = add_med_btn
        self.vitals_label = vitals_label
        self.vitals_list = vitals_list
        self.show_more_vitals_btn = show_more_vitals_btn
        self.add_vitals_btn = add_vitals_btn
        self.logout_btn = logout_btn
        self.med_list.bind(minimum_height=self.med_list.setter('height'))
        # Load data after widgets are initialized
        self.show_medication()
        self.show_vitals()
        self.manager.get_screen("add_med").set_token(self.token)

    def open_add_vitals(self, instance):
        self.manager.current = "add_vitals"
        self.manager.get_screen("add_vitals").set_token(self.token)

    def logout(self, instance):
        self.token = None
        login_screen = self.manager.get_screen("login")
        login_screen.email_input.text = ""
        login_screen.password_input.text = ""
        self.manager.current = "login"

class AddMedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.name_input = TextInput(hint_text='Medication Name', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.dosage_input = TextInput(hint_text='Dosage', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.times_input = TextInput(hint_text='Times (e.g. 08:00,20:00)', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.start_date_input = TextInput(hint_text='Start Date (YYYY-MM-DD)', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.end_date_input = TextInput(hint_text='End Date (YYYY-MM-DD)', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.quantity_input = TextInput(hint_text='Quantity', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        save_btn = Button(text='Save', size_hint=(None, None), width=250, height=40, pos_hint={'center_x': 0.5})
        save_btn.bind(on_press=self.save_med)
        back_btn = Button(text='Back', size_hint=(None, None), width=250, height=40, pos_hint={'center_x': 0.5})
        back_btn.bind(on_press=self.go_back)
        self.message_label = Label(text='')
        layout.add_widget(self.name_input)
        layout.add_widget(self.dosage_input)
        layout.add_widget(self.times_input)
        layout.add_widget(self.start_date_input)
        layout.add_widget(self.end_date_input)
        layout.add_widget(self.quantity_input)
        layout.add_widget(save_btn)
        layout.add_widget(back_btn)
        layout.add_widget(self.message_label)
        self.add_widget(layout)
        self.token = None

    def set_token(self, token):
        self.token = token

    def save_med(self, instance):
        name = self.name_input.text.strip()
        dose = self.dosage_input.text.strip()
        times_raw = self.times_input.text.strip()
        start_date = self.start_date_input.text.strip()
        end_date = self.end_date_input.text.strip()
        quantity = self.quantity_input.text.strip()
        headers = {"Authorization": f"Bearer {self.token}"}
        times = [t.strip() for t in times_raw.split(",") if t.strip()]
        med_data = {"name": name, "dose": dose, "times": times}
        if start_date:
            med_data["start_date"] = start_date
        if end_date:
            med_data["end_date"] = end_date
        if quantity:
            try:
                med_data["quantity"] = int(quantity)
            except ValueError:
                self.message_label.text = "Quantity must be a number."
                return
        try:
            response = requests.post(f"{API_BASE}/meds", json=med_data, headers=headers)
            if response.status_code == 200 or response.status_code == 201:
                self.message_label.text = "Medication added!"
                # Clear form fields after successful add
                self.name_input.text = ""
                self.dosage_input.text = ""
                self.times_input.text = ""
                self.start_date_input.text = ""
                self.end_date_input.text = ""
                self.quantity_input.text = ""
                # Go back to main screen and refresh meds
                self.manager.current = "main"
                self.manager.get_screen("main").show_medication()
            else:
                self.message_label.text = "Failed to add medication."
        except Exception as e:
            self.message_label.text = f"Error: {e}"

    def go_back(self, instance):
        self.manager.current = "main"

class AddVitalsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.bp_input = TextInput(hint_text='Blood Pressure', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.hr_input = TextInput(hint_text='Heart Rate', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        self.temp_input = TextInput(hint_text='Temperature', multiline=False, size_hint=(None, None), width=250, height=35, pos_hint={'center_x': 0.5})
        save_btn = Button(text='Save', size_hint=(None, None), width=250, height=40, pos_hint={'center_x': 0.5})
        save_btn.bind(on_press=self.save_vitals)
        back_btn = Button(text='Back', size_hint=(None, None), width=250, height=40, pos_hint={'center_x': 0.5})
        back_btn.bind(on_press=self.go_back)
        self.message_label = Label(text='')
        layout.add_widget(self.bp_input)
        layout.add_widget(self.hr_input)
        layout.add_widget(self.temp_input)
        layout.add_widget(save_btn)
        layout.add_widget(back_btn)
        layout.add_widget(self.message_label)
        self.add_widget(layout)
        self.token = None

    def set_token(self, token):
        self.token = token

    def save_vitals(self, instance):
        import datetime
        bp = self.bp_input.text.strip()
        hr = self.hr_input.text.strip()
        temp = self.temp_input.text.strip()
        headers = {"Authorization": f"Bearer {self.token}"}
        if not (bp or hr or temp):
            self.message_label.text = "Please enter at least one value."
            return
        vital_data = {
            "bp": bp if bp else None,
            "hr": hr if hr else None,
            "temp": temp if temp else None,
            "record_time": datetime.datetime.now().isoformat()
        }
        try:
            response = requests.post(f"{API_BASE}/vitals", json=vital_data, headers=headers)
            if response.status_code == 200:
                self.message_label.text = "Vitals added!"
                self.manager.get_screen("main").show_vitals()
                # Clear form fields after successful add
                self.bp_input.text = ""
                self.hr_input.text = ""
                self.temp_input.text = ""
                self.manager.current = "main"
            else:
                self.message_label.text = "Failed to add vitals."
        except Exception as e:
            self.message_label.text = f"Error: {e}"

    def go_back(self, instance):
        self.manager.current = "main"

class MedBuddyApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MainScreen(name="main"))
        sm.add_widget(AddMedScreen(name="add_med"))
        sm.add_widget(AddVitalsScreen(name="add_vitals"))
        return sm

if __name__ == "__main__":
    MedBuddyApp().run()
    # End of file. All stray code after this line is removed.
