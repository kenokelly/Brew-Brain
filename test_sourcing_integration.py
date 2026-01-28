import sys
import os
from unittest.mock import MagicMock, patch

# Mock missing dependencies
sys.modules['influxdb_client'] = MagicMock()
sys.modules['influxdb_client.client.write_api'] = MagicMock()
sys.modules['serpapi'] = MagicMock() # Mock serpapi directly too
sys.modules['pandas'] = MagicMock() # Just in case

# Add app to path
sys.path.append(os.getcwd())

# Mock configuration
with patch('app.services.sourcing.get_config') as mock_config:
    mock_config.return_value = "fake_api_key"
    
    # Import SUT
    from app.services import sourcing

    def test_integration():
        print("Testing compare_recipe_prices with mocked SerpApi...")
        
        # Test Data: Recipe needs 200g of Citra
        recipe = {
            "hops": [{"name": "Citra", "amount": 200}], # 200g needed
            "fermentables": [],
            "yeasts": []
        }
        
        # Mock SerpApi Response
        mock_results_tmm = {
            "organic_results": [
                {
                    "title": "Citra Hops 100g - The Malt Miller",
                    "link": "https://themaltmiller.co.uk/citra",
                    "snippet": "Buy Citra Hops. Price: £7.50 for 100g pack.",
                    "rich_snippet": {
                        "top": {
                            "detected_extensions": {
                                "price": "7.50"
                            }
                        }
                    }
                }
            ]
        }
        
        mock_results_geb = {
            "organic_results": [
                {
                    "title": "Citra Hops - Get Er Brewed",
                    "link": "https://geterbrewed.com/citra",
                    "snippet": "Citra Hops 2023 50g 4.00 GBP.", # 50g pack
                }
            ]
        }
        
        # Mock Page Content to force specific weights if visitor visits
        # We'll rely on snippet parsing for this test to keep it simple, 
        # as get_page_content is not mocked here but let's mock it to be safe
        
        with patch('app.services.sourcing.GoogleSearch') as MockSearch, \
             patch('app.services.sourcing.get_page_content') as MockPage:
            
            # Mock Page Content for TMM (visitor)
            MockPage.return_value = """
                <html>
                    <h1 class="product_title">Citra Hops 100g</h1>
                    <div class="price"><span class="amount">£7.50</span></div>
                </html>
            """
            
            # Mock Page Content for GEB (visitor) -- assuming code visits top hit
            # Note: GEB mock snippet says 50g, let's make page say 50g too
            
            # We need to return different results based on the query
            def side_effect(params):
                query = params['q']
                mock_instance = MagicMock()
                
                if "themaltmiller" in query:
                    mock_instance.get_dict.return_value = mock_results_tmm
                elif "geterbrewed" in query:
                    mock_instance.get_dict.return_value = mock_results_geb
                else:
                    mock_instance.get_dict.return_value = {"organic_results": []}
                    
                return mock_instance

            MockSearch.side_effect = side_effect
            
            # Run Code
            result = sourcing.compare_recipe_prices(recipe)
            
            print(f"DEBUG: Full Result Type: {type(result)}")
            print(f"DEBUG: Full Result: {result}")

            if isinstance(result, dict) and "error" in result:
                print(f"❌ API Returned Error: {result['error']}")
                return

            if not result:
                print("❌ API Returned Empty Result")
                return

            # Analysis
            breakdown = result.get('breakdown', [])
            if not breakdown:
                print("❌ No items in breakdown")
                return
                
            row = breakdown[0] # First ingredient (Citra)
            print("\nResult Breakdown for Citra (Need 200g):")
            print(f"  TMM Price (100g pack): £{row['tmm_price']}")
            print(f"  TMM Total Cost (Assumed): £{row['tmm_cost']}")
            print(f"  GEB Price (50g pack): £{row['geb_price']}")
            print(f"  GEB Total Cost (Assumed): £{row['geb_cost']}")
            
            # Assertions
            # TMM: £7.50 for 100g -> £0.075/g. Need 200g -> £15.00
            if row['tmm_cost'] == 15.0: print("✅ TMM Cost Correct (£15.00)")
            else: print(f"❌ TMM Cost Failed: Got {row['tmm_cost']}, Expected 15.0")
            
            # GEB: £4.00 for 50g -> £0.08/g. Need 200g -> £16.00
            # Note: snippet parsing for GEB needs to catch "50g"
            if row['geb_cost'] == 16.0: print("✅ GEB Cost Correct (£16.00)")
            else: print(f"❌ GEB Cost Failed: Got {row['geb_cost']}, Expected 16.0")

    if __name__ == "__main__":
        try:
            test_integration()
        except Exception as e:
            print(f"Test Failed: {e}")
            import traceback
            traceback.print_exc()
