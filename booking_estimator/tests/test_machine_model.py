import pytest
from booking_estimator.machine_model import MachineConfig
def test_config():
 assert MachineConfig("test",60,12).to_dict()["machine_id"]=="test"
 with pytest.raises(ValueError): MachineConfig("test",60,0)
