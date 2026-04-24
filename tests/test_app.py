"""Pytest test suite for ACEest Fitness & Gym Flask API"""

import os
import pytest

os.environ["DB_NAME"] = ":memory:"

from app import app, init_db, calculate_bmi, calculate_calories, PROGRAMS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------

class TestCalculateBMI:
    def test_normal_bmi(self):
        result = calculate_bmi(70, 175)
        assert result["bmi"] == 22.9
        assert result["category"] == "Normal"

    def test_underweight(self):
        result = calculate_bmi(45, 175)
        assert result["category"] == "Underweight"

    def test_overweight(self):
        result = calculate_bmi(85, 170)
        assert result["category"] == "Overweight"

    def test_obese(self):
        result = calculate_bmi(110, 170)
        assert result["category"] == "Obese"

    def test_zero_height_returns_empty(self):
        assert calculate_bmi(70, 0) == {}

    def test_zero_weight_returns_empty(self):
        assert calculate_bmi(0, 175) == {}


class TestCalculateCalories:
    def test_fat_loss_3day(self):
        cal = calculate_calories(80, "Fat Loss (FL) - 3 day")
        assert cal == 1760  # 80 * 22

    def test_muscle_gain(self):
        cal = calculate_calories(80, "Muscle Gain (MG) - PPL")
        assert cal == 2800  # 80 * 35

    def test_unknown_program_returns_none(self):
        assert calculate_calories(80, "Unknown Program") is None

    def test_zero_weight_returns_none(self):
        assert calculate_calories(0, "Beginner (BG)") is None


# ---------------------------------------------------------------------------
# Health & info endpoint tests
# ---------------------------------------------------------------------------

class TestInfoEndpoints:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["app"] == "ACEest Fitness & Gym"
        assert "version" in data

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "healthy"

    def test_programs_endpoint(self, client):
        resp = client.get("/programs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "Beginner (BG)" in data
        assert "Fat Loss (FL) - 3 day" in data


# ---------------------------------------------------------------------------
# Client CRUD tests
# ---------------------------------------------------------------------------

class TestClientCRUD:
    def test_create_client_success(self, client):
        resp = client.post("/clients", json={
            "name": "Arjun Kumar",
            "age": 28,
            "height": 175.0,
            "weight": 78.0,
            "program": "Fat Loss (FL) - 3 day",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Arjun Kumar"
        assert data["calories"] == 1716  # 78 * 22

    def test_create_client_missing_name(self, client):
        resp = client.post("/clients", json={"age": 25})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_duplicate_client(self, client):
        payload = {"name": "Priya S", "age": 30}
        client.post("/clients", json=payload)
        resp = client.post("/clients", json=payload)
        assert resp.status_code == 409

    def test_list_clients(self, client):
        client.post("/clients", json={"name": "Client A"})
        client.post("/clients", json={"name": "Client B"})
        resp = client.get("/clients")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.get_json()]
        assert "Client A" in names
        assert "Client B" in names

    def test_get_client_found(self, client):
        client.post("/clients", json={"name": "Ravi M", "age": 35})
        resp = client.get("/clients/Ravi M")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Ravi M"

    def test_get_client_not_found(self, client):
        resp = client.get("/clients/NonExistent")
        assert resp.status_code == 404

    def test_update_client(self, client):
        client.post("/clients", json={"name": "Meena L", "weight": 65.0, "program": "Beginner (BG)"})
        resp = client.put("/clients/Meena L", json={"age": 25, "weight": 63.0})
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Meena L"

    def test_update_nonexistent_client(self, client):
        resp = client.put("/clients/Ghost", json={"age": 30})
        assert resp.status_code == 404

    def test_delete_client(self, client):
        client.post("/clients", json={"name": "TempClient"})
        resp = client.delete("/clients/TempClient")
        assert resp.status_code == 200
        assert client.get("/clients/TempClient").status_code == 404

    def test_delete_nonexistent_client(self, client):
        resp = client.delete("/clients/Nobody")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Progress tests
# ---------------------------------------------------------------------------

class TestProgress:
    def _create(self, client):
        client.post("/clients", json={"name": "SampleUser"})

    def test_add_progress_success(self, client):
        self._create(client)
        resp = client.post("/clients/SampleUser/progress", json={"adherence": 85})
        assert resp.status_code == 201
        assert resp.get_json()["adherence"] == 85

    def test_add_progress_missing_adherence(self, client):
        self._create(client)
        resp = client.post("/clients/SampleUser/progress", json={})
        assert resp.status_code == 400

    def test_add_progress_out_of_range(self, client):
        self._create(client)
        resp = client.post("/clients/SampleUser/progress", json={"adherence": 120})
        assert resp.status_code == 400

    def test_get_progress(self, client):
        self._create(client)
        client.post("/clients/SampleUser/progress", json={"adherence": 70})
        client.post("/clients/SampleUser/progress", json={"adherence": 80})
        resp = client.get("/clients/SampleUser/progress")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2


# ---------------------------------------------------------------------------
# Workout tests
# ---------------------------------------------------------------------------

class TestWorkouts:
    def _create(self, client):
        client.post("/clients", json={"name": "WorkoutUser"})

    def test_add_workout_success(self, client):
        self._create(client)
        resp = client.post("/clients/WorkoutUser/workouts", json={
            "workout_type": "Strength",
            "duration_min": 60,
            "exercises": [{"name": "Squat", "sets": 5, "reps": 5, "weight": 100}],
        })
        assert resp.status_code == 201
        assert "workout_id" in resp.get_json()

    def test_add_workout_missing_type(self, client):
        self._create(client)
        resp = client.post("/clients/WorkoutUser/workouts", json={"duration_min": 45})
        assert resp.status_code == 400

    def test_get_workouts(self, client):
        self._create(client)
        client.post("/clients/WorkoutUser/workouts", json={"workout_type": "Conditioning"})
        resp = client.get("/clients/WorkoutUser/workouts")
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------

class TestMetrics:
    def _create(self, client):
        client.post("/clients", json={"name": "MetricsUser"})

    def test_add_metrics_success(self, client):
        self._create(client)
        resp = client.post("/clients/MetricsUser/metrics", json={
            "weight": 75.0,
            "waist": 85.0,
            "bodyfat": 18.0,
        })
        assert resp.status_code == 201

    def test_get_metrics(self, client):
        self._create(client)
        client.post("/clients/MetricsUser/metrics", json={"weight": 75.0})
        resp = client.get("/clients/MetricsUser/metrics")
        assert resp.status_code == 200
        assert len(resp.get_json()) >= 1


# ---------------------------------------------------------------------------
# BMI endpoint tests
# ---------------------------------------------------------------------------

class TestBMIEndpoint:
    def test_bmi_success(self, client):
        client.post("/clients", json={"name": "BMIUser", "weight": 70.0, "height": 175.0})
        resp = client.get("/clients/BMIUser/bmi")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "bmi" in data
        assert "category" in data

    def test_bmi_client_not_found(self, client):
        resp = client.get("/clients/NobodyBMI/bmi")
        assert resp.status_code == 404

    def test_bmi_insufficient_data(self, client):
        client.post("/clients", json={"name": "NoDimUser"})
        resp = client.get("/clients/NoDimUser/bmi")
        assert resp.status_code == 400
