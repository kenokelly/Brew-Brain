import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Mock github dependency
mock_github_module = MagicMock()
sys.modules['github'] = mock_github_module

# Mock core.config dependency to avoid import errors related to influxdb_client
mock_core_config = MagicMock()
mock_core_config.get_config.return_value = None
sys.modules['core.config'] = mock_core_config

# Now we can import the service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
from services.github_integration import push_recipe_to_repo

class TestGithubIntegration(unittest.TestCase):
    def setUp(self):
        # Reset mocks before each test
        mock_github_module.reset_mock()
        self.mock_g = MagicMock()
        self.mock_repo = MagicMock()
        mock_github_module.Github.return_value = self.mock_g
        self.mock_g.get_repo.return_value = self.mock_repo

        # Reset the side_effect to ensure normal mock behavior by default
        mock_github_module.Github.side_effect = None

    def test_push_recipe_with_xml_content_update_existing(self):
        # Setup
        recipe_data = {"name": "My Great Beer", "xml_content": "<xml>content</xml>"}
        token = "fake_token"
        repo_name = "user/repo"

        # Mock get_contents to succeed, simulating existing file
        mock_contents = MagicMock()
        mock_contents.path = "recipes/My_Great_Beer.xml"
        mock_contents.sha = "fake_sha"
        self.mock_repo.get_contents.return_value = mock_contents

        # Execute
        result = push_recipe_to_repo(recipe_data, token, repo_name)

        # Assert
        mock_github_module.Github.assert_called_once_with(token)
        self.mock_g.get_repo.assert_called_once_with(repo_name)
        self.mock_repo.get_contents.assert_called_once_with("recipes/My_Great_Beer.xml")
        self.mock_repo.update_file.assert_called_once_with(
            "recipes/My_Great_Beer.xml",
            "Update recipe My_Great_Beer",
            "<xml>content</xml>",
            "fake_sha"
        )
        self.assertEqual(result, {"status": "success", "message": f"Updated recipes/My_Great_Beer.xml in {repo_name}"})

    def test_push_recipe_with_xml_content_create_new(self):
        # Setup
        recipe_data = {"name": "New Beer", "xml_content": "<xml>new</xml>"}
        token = "fake_token"
        repo_name = "user/repo"

        # Mock get_contents to raise exception, simulating non-existent file
        self.mock_repo.get_contents.side_effect = Exception("Not Found")

        # Execute
        result = push_recipe_to_repo(recipe_data, token, repo_name)

        # Assert
        self.mock_repo.get_contents.assert_called_once_with("recipes/New_Beer.xml")
        self.mock_repo.create_file.assert_called_once_with(
            "recipes/New_Beer.xml",
            "Add recipe New_Beer",
            "<xml>new</xml>"
        )
        self.mock_repo.update_file.assert_not_called()
        self.assertEqual(result, {"status": "success", "message": f"Created recipes/New_Beer.xml in {repo_name}"})

    def test_push_recipe_fallback_xml_generation(self):
        # Setup
        recipe_data = {
            "name": "Fallback Beer",
            "og": "1.050",
            "ibu": "30",
            "abv": "5.0",
            "source_url": "http://example.com"
        }
        token = "fake_token"
        repo_name = "user/repo"

        self.mock_repo.get_contents.side_effect = Exception("Not Found")

        # Execute
        result = push_recipe_to_repo(recipe_data, token, repo_name)

        # Assert
        self.mock_repo.create_file.assert_called_once()
        args, kwargs = self.mock_repo.create_file.call_args
        self.assertEqual(args[0], "recipes/Fallback_Beer.xml")
        self.assertEqual(args[1], "Add recipe Fallback_Beer")
        self.assertIn("<NAME>Fallback Beer</NAME>", args[2])
        self.assertIn("<OG>1.050</OG>", args[2])
        self.assertIn("<IBU>30</IBU>", args[2])
        self.assertIn("<EST_ABV>5.0</EST_ABV>", args[2])
        self.assertIn("<SOURCE>http://example.com</SOURCE>", args[2])
        self.assertEqual(result, {"status": "success", "message": f"Created recipes/Fallback_Beer.xml in {repo_name}"})

    def test_push_recipe_missing_xml_content_with_xml_url(self):
        # Setup
        recipe_data = {
            "name": "Missing XML",
            "source_url": "http://example.com/recipe.xml"
        }
        token = "fake_token"
        repo_name = "user/repo"

        # Execute
        result = push_recipe_to_repo(recipe_data, token, repo_name)

        # Assert
        self.assertEqual(result, {"error": "No XML content provided to save."})
        self.mock_repo.get_contents.assert_not_called()
        self.mock_repo.create_file.assert_not_called()
        self.mock_repo.update_file.assert_not_called()

    def test_push_recipe_github_exception(self):
        # Setup
        recipe_data = {"name": "Error Beer"}
        token = "fake_token"
        repo_name = "user/repo"

        # Mock Github init to raise exception
        mock_github_module.Github.side_effect = Exception("API Error")

        # Execute
        result = push_recipe_to_repo(recipe_data, token, repo_name)

        # Assert
        self.assertEqual(result, {"error": "API Error"})
        self.mock_repo.get_contents.assert_not_called()

if __name__ == '__main__':
    unittest.main()
