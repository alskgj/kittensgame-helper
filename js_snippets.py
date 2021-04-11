from jinja2 import Template

# prices
"""
gamePage.bldTab.children[18].model.prices
(3) […]
​0: Object { val: 2853.987852346672, name: "steel" }
​1: Object { val: 1426.993926173336, name: "gear" }
​2: Object { val: 1426.993926173336, name: "scaffold" }
"""


all_buildable = """
var buildable_right_now  = [];
for (btn of gamePage.bldTab.children) {
  if (btn.model.enabled && btn.model.hasOwnProperty("metadata")) {
    buildable_right_now.push(btn.model.metadata.name);
    }
}

return buildable_right_now;
"""

buildable_with_prices = """
var prices = [];
for (btn of gamePage.bldTab.children) {
  if (btn.model.enabled && btn.model.hasOwnProperty("metadata")) {
    let obj = {name: btn.model.metadata.name};
    let resources = [];
    for (element of btn.model.prices) {
      resources.push(element.name);
    }
    obj["resources"] = resources;
    prices.push(obj);
  }
}
return prices;"""

build_x = Template("""
for (btn of gamePage.bldTab.children) {
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


add_pause_all_button = '$("#footerLinks").append(' \
                      '\'<div><button id="toggleScript" style="color:black" ' \
                      'onclick="theButton()">Pause script...</button>' \
                      '</br></div>\');'

function_button_pause_all = """
window.script_paused = false;
window.theButton = function() {
if (document.getElementById("toggleScript").style.color == "black") {
    document.getElementById("toggleScript").style.color = 'red';
    gamePage.msg('Script is now paused!');
    window.script_paused = true;
} else {
    document.getElementById("toggleScript").style.color = 'black';
    gamePage.msg('Script is now running!');
    window.script_paused = false;
}
}
"""