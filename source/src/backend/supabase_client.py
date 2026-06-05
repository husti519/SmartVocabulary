import os
from supabase import create_client, Client
from supabase_auth.errors import AuthError
from ..utils.config_manager import ConfigManager
from ..utils.logger import log_exception

class SupabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseManager, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        # 1. Try ConfigManager first
        url, key = ConfigManager.get_supabase_config()

        if not url or not key:
            self.client = None
        else:
            self.client: Client = create_client(url, key)
            self.user = None

    def update_config(self, url, key):
        """Updates the internal client and saves credentials to the config file."""
        ConfigManager.save_supabase_config(url, key)
        self.client = create_client(url, key)
        return True

    @staticmethod
    def test_connection(url, key):
        """Tests if the provided URL and Key can establish a connection to Supabase."""
        try:
            # Create a temporary client to test credentials
            temp_client: Client = create_client(url, key)
            # Perform a simple metadata query to verify the key
            # Fetching settings is a lightweight way to check if the connection is active
            temp_client.auth.get_session()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Authentication ---
    def sign_up(self, email, password, username):
        try:
            response = self.client.auth.sign_up({
                "email": email, 
                "password": password,
                "options": {
                    "data": {
                        "username": username
                    }
                }
            })
            self.user = response.user
            return response
        except AuthError as e:
            return {"error": str(e)}
        except Exception as e:
            log_exception("SupabaseManager.sign_up", "Technical exception during sign up", e)
            return {"error": f"Network or system error: {str(e)}"}

    def sign_in(self, email, password):
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            self.user = response.user
            return response
        except AuthError as e:
            return {"error": str(e)}
        except Exception as e:
            log_exception("SupabaseManager.sign_in", "Technical exception during sign in", e)
            return {"error": f"Network or system error: {str(e)}"}

    def sign_out(self):
        if self.client:
            self.client.auth.sign_out()
        self.user = None

    def withdraw_user(self):
        """Calls the RPC function delete_user to remove the current user account."""
        try:
            if not self.client or not self.user:
                return {"success": False, "error": "로그인 정보가 없습니다."}
            
            # Call the PostgreSQL function defined in schema.sql
            # delete_user() is a SECURITY DEFINER function that deletes from auth.users where id = auth.uid()
            self.client.rpc("delete_user").execute()
            
            # Sign out locally (the server session is already invalid)
            self.sign_out()
            return {"success": True}
        except Exception as e:
            log_exception("SupabaseManager.withdraw_user", "Account withdrawal failed", e)
            return {"success": False, "error": str(e)}

    def send_password_reset_email(self, email):
        """Sends a password reset link/code to the user's email."""
        try:
            # Supabase will send a 6-digit OTP code if configured correctly in Auth > Providers > Email
            self.client.auth.reset_password_for_email(email)
            return {"success": True}
        except Exception as e:
            log_exception("SupabaseManager", "Error occurred", e)
            return {"error": str(e)}

    def verify_otp(self, email, token, type="signup"):
        """Verifies the OTP code sent via email. Type can be 'signup', 'recovery', etc."""
        try:
            response = self.client.auth.verify_otp({"email": email, "token": token, "type": type})
            self.user = response.user
            return {"success": True, "user": response.user}
        except Exception as e:
            log_exception("SupabaseManager", "Error occurred during OTP verification", e)
            return {"error": str(e)}

    def resend_signup_otp(self, email):
        """Resends the signup verification code to the specified email."""
        try:
            if not self.client:
                return {"error": "Supabase client not initialized"}
            
            self.client.auth.resend({
                "type": "signup",
                "email": email
            })
            return {"success": True}
        except Exception as e:
            log_exception("SupabaseManager.resend_signup_otp", "Failed to resend OTP", e)
            return {"error": str(e)}

    def update_password(self, new_password, current_password=None):
        """Updates the current user's password. User must be authenticated or in a recovery session."""
        try:
            attributes = {"password": new_password}
            if current_password:
                attributes["current_password"] = current_password
            
            self.client.auth.update_user(attributes)
            return {"success": True}
        except Exception as e:
            log_exception("SupabaseManager", "Error occurred during password update", e)
            return {"error": str(e)}

    # --- Card Sets ---
    def get_card_sets(self):
        """Fetches all card sets with card counts for the current user."""
        if not self.client or not self.user: return []
        response = self.client.table("card_sets")\
            .select("*, cards(count)")\
            .eq("user_id", self.user.id)\
            .order("created_at", desc=True)\
            .execute()
        return response.data

    def create_card_set(self, title, description=""):
        if not self.client or not self.user: return None
        data = {
            "user_id": self.user.id,
            "title": title,
            "description": description
        }
        response = self.client.table("card_sets").insert(data).execute()
        return response.data

    def delete_card_set(self, set_id):
        if not self.client: return None
        response = self.client.table("card_sets").delete().eq("id", set_id).execute()
        return response.data

    def update_card_set(self, set_id, title, description=""):
        """Updates the title and description of an existing card set."""
        if not self.client: return None
        data = {
            "title": title,
            "description": description
        }
        response = self.client.table("card_sets").update(data).eq("id", set_id).execute()
        return response.data

    def delete_all_cards_in_set(self, set_id):
        """Removes all cards belonging to a specific set."""
        if not self.client: return None
        response = self.client.table("cards").delete().eq("cardset_id", set_id).execute()
        return response.data

    def update_last_studied(self, set_id):
        """Updates the last_studied_at timestamp for a specific card set."""
        if not self.client: return None
        from datetime import datetime
        now = datetime.now().isoformat()
        response = self.client.table("card_sets").update({"last_studied_at": now}).eq("id", set_id).execute()
        return response.data

    def get_recent_card_sets(self, limit=3):
        """Fetches the most recently studied card sets for the current user."""
        if not self.client or not self.user: return []
        response = self.client.table("card_sets")\
            .select("*, cards(count)")\
            .eq("user_id", self.user.id)\
            .not_.is_("last_studied_at", "null")\
            .order("last_studied_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data

    # --- Cards ---
    def get_cards(self, cardset_id):
        if not self.client: return []
        # Explicitly order by created_at and id to maintain original insertion/CSV order
        response = self.client.table("cards")\
            .select("*")\
            .eq("cardset_id", cardset_id)\
            .order("created_at", desc=False)\
            .execute()
        return response.data

    def add_card(self, cardset_id, word, definition, is_oxford=False):
        if not self.client or not self.user: return None
        data = {
            "user_id": self.user.id,
            "cardset_id": cardset_id,
            "word": word,
            "definition": definition
        }
        response = self.client.table("cards").insert(data).execute()
        return response.data

    def update_card_star(self, card_id, is_starred):
        """Toggles the starred status for a specific card."""
        if not self.client: return None
        response = self.client.table("cards").update({"starred": is_starred}).eq("id", card_id).execute()
        return response.data

    def search_words(self, query):
        """Searches for words matching the query and returns them with their card sets."""
        if not self.client or not self.user: return []
        # Join with card_sets to get title
        response = self.client.table("cards")\
            .select("*, card_sets(id, title)")\
            .eq("user_id", self.user.id)\
            .ilike("word", f"%{query}%")\
            .execute()
        return response.data

    def move_cards(self, card_ids, target_set_id):
        """Moves multiple cards to a different card set."""
        if not self.client or not card_ids: return False
        try:
            # We use .in_() to match multiple IDs
            response = self.client.table("cards")\
                .update({"cardset_id": target_set_id})\
                .in_("id", card_ids)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            log_exception("SupabaseManager.move_cards", "Failed to move cards", e)
            return False

    def delete_cards_bulk(self, card_ids):
        """Deletes multiple cards at once."""
        if not self.client or not card_ids: return False
        try:
            response = self.client.table("cards")\
                .delete()\
                .in_("id", card_ids)\
                .execute()
            return len(response.data) > 0
        except Exception as e:
            log_exception("SupabaseManager.delete_cards_bulk", "Failed to delete cards", e)
            return False

    def import_from_csv(self, file_path, custom_title=None):
        """Parses a CSV file and inserts a new card set and its cards into Supabase."""
        from ..utils.csv_parser import SmartCSVParser
        import os
        
        if not self.client or not self.user: return {"error": "Not authenticated"}

        file_name = os.path.basename(file_path)
        set_title = custom_title if custom_title else os.path.splitext(file_name)[0]
        
        try:
            # 1. Parse and Prepare Cards using SmartCSVParser
            parser = SmartCSVParser()
            parsed_cards = parser.import_csv(file_path)
            
            if not parsed_cards:
                return {"error": "No valid cards found in the CSV file"}

            # 2. Create the Card Set
            set_data = {
                "user_id": self.user.id,
                "title": set_title,
                "description": f"Imported from {file_name}"
            }
            # Handle potential duplicate title error
            set_response = self.client.table("card_sets").insert(set_data).execute()
            if not set_response.data:
                return {"error": "Failed to create card set (it might already exist)"}
            
            new_set_id = set_response.data[0]['id']
            
            # 3. Batch Insert Cards
            cards_to_insert = []
            for card in parsed_cards:
                cards_to_insert.append({
                    "user_id": self.user.id,
                    "cardset_id": new_set_id,
                    "word": card["word"],
                    "definition": card["definition"]
                })
            
            if cards_to_insert:
                # Supabase handles batch inserts if you pass a list of dicts
                # Note: Insert in chunks if the list is extremely large (e.g., > 1000)
                chunk_size = 500
                for i in range(0, len(cards_to_insert), chunk_size):
                    chunk = cards_to_insert[i:i + chunk_size]
                    self.client.table("cards").insert(chunk).execute()
                
                return {"success": True, "set_id": new_set_id, "count": len(cards_to_insert)}
            
            return {"success": True, "set_id": new_set_id, "count": 0}

        except Exception as e:
            # Revert set creation if something goes wrong? (Supabase doesn't have transactions across table calls easily)
            return {"error": str(e)}
