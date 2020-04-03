<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title></title>
<style type="text/css">
.sub-report-title {}
.run-title {}

h1 { padding-top: 35px; }
h2 { padding-top: 20px; }
h3 { padding-top: 15px; }

.elem-desc {}
.elem-filename {}

div.elem-image {
  width: 100%;
  page-break-before:always;
}

.elem-image object.svg-reportlet {
    width: 100%;
    padding-bottom: 5px;
}
body {
    padding: 10px 10px 10px;
}
</style>
</head>
<body>
<ul>
    <li><a href=#Summary>Summary</a></li>
{% for section in sections %}
    <li><a href=#{{section}}>{{section}}</a></li>
{% endfor %}
</ul>
    <div id="summary">
        <h1 class="sub-report-title">Summary</h1>
        <ul>
        {% for bullet in summary['bullets'] %}
            <li>{{bullet}}: {{summary['bullets'][bullet]}}</li>
        {% endfor %}
        </ul>
    <div>
{% for section in sections %}
    <div id="{{ section }}">
        <h1 class="sub-report-title">{{ section }}</h1>
        {% for sub_section in sections[section] %}
            <h2 class="sub-report-title">{{ sub_section }}</h2>
            <ul>
            {% for bullet in sections[section][sub_section]['bullets'] %}
                <li>{{bullet}}: {{sections[section][sub_section]['bullets'][bullet]}}</li>
            {% endfor %}
            </ul>
            <p>{{sections[section][sub_section]['description']}}</p>
            {% for figure in sections[section][sub_section]['figures'] %}
                <div class="elem-image">
                    <object class="svg-reportlet" type="image/svg+xml" data="./{{ figure }}">
                    Problem loading figure {{ figure }}. If the link below works, please try reloading the report in your browser.</object>
                </div>
                <div class="elem-filename">
                    Get figure file: <a href="./{{ figure }}" target="_blank">{{ figure }}</a>
                </div>
            {% endfor %} 
        {% endfor %}
    </div>
{% endfor %}
</body>
</html>