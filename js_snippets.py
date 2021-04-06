from jinja2 import Template

all_buildable = """
var buildable_right_now  = []
for (btn of gamePage.bldTab.buttons) {
  if (btn.model.enabled && btn.model.hasOwnProperty("metadata")) {
    buildable_right_now.push(btn.model.metadata.name);
    }
}
return buildable_right_now;
"""

build_x = Template("""
for (btn of gamePage.bldTab.buttons) {
  if (btn.model.enabled && btn.model.hasOwnProperty("metadata") && btn.model.metadata.name == '{{ x }}') {
    btn.buttonContent.click();
    }
}
""")

upgrade_embassies = """
for (racePanel of gamePage.diplomacyTab.racePanels) {
    if (racePanel.embassyButton.model.enabled) {
        racePanel.embassyButton.buttonContent.click();
    }
}
"""