import unittest  # Import the testing framework

# Create a test loader - this helps find our tests
loader = unittest.TestLoader()

# Look for test files in the 'tests' folder
start_dir = "./tests"

# Find all files that start with 'test_'
files = loader.discover(start_dir, pattern="test_*.py")

# Only run the tests if we run this file directly
if __name__ == "__main__":
    # Create a test runner that will display detailed results
    runner = unittest.TextTestRunner()
    # Run all the tests we found
    runner.run(files)
