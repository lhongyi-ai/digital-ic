import json
from pathlib import Path
import shlex

import pytest

from vibfpga.project_profile import ROOT, command_list, load_profile, main


@pytest.mark.parametrize("name,n,lanes", [("cwru-neighbor3", 1024, 4), ("sen1-spectrum", 256, 1), ("fcl1-fixture", 256, 1)])
def test_profiles_bind_existing_models(name, n, lanes):
    p = load_profile(name)
    assert (p["n"], p["lanes"]) == (n, lanes)
    assert Path(p["model"]).is_absolute()
    assert not p["real_field_model_trained"]
    if name == "fcl1-fixture":
        assert "not_for_deployment" in p["model_training_status"]


def test_profile_rejects_model_mismatch(tmp_path):
    config = json.loads((ROOT / "configs/project-profiles.json").read_text())
    config["profiles"]["cwru-neighbor3"]["n"] = 256
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="window length.*mismatch"):
        load_profile(config=path)
    with pytest.raises(ValueError, match="unknown profile"):
        load_profile("imaginary")


def test_profile_shell_export_and_commands_quote_paths(capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    main(["export", "--format", "shell"])
    exports = dict(shlex.split(line)[1].split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert exports["VIB_MODEL"] == str(ROOT / "artifacts/model_neighbor/model.json")
    command = shlex.split(command_list(load_profile())[0])
    assert command[0] == str(ROOT / ".venv/bin/python")
    assert command[command.index("--lanes") + 1] == "4"


def test_profile_commands_select_board_clock_and_measurement_role(capsys):
    board = shlex.split(command_list(load_profile())[1])
    assert Path(board[1]).name == "build_board.py"
    assert board[board.index("--clock-source") + 1] == "external12"
    main(["commands", "--clock-source", "hfosc12"])
    board = shlex.split(capsys.readouterr().out.splitlines()[1])
    assert board[board.index("--clock-source") + 1] == "hfosc12"
    main(["export", "--clock-source", "hfosc12"])
    exported = json.loads(capsys.readouterr().out)
    assert exported["clock_source"] == "hfosc12" and not exported["hardware_evidence_checked"]
    sensor = shlex.split(command_list(load_profile("sen1-spectrum"))[0])
    assert sensor[sensor.index("--rate") + 1] == "800"
    assert sensor[sensor.index("--axis") + 1] == "2"
    # build_sensor defaults to spectrum enabled and offers --no-spectrum to disable it.
    assert "--no-spectrum" not in sensor
