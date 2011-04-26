function ShowPop(id)
{
    if (document.getElementById)
    {
           document.getElementById(id).style.visibility = " visible";
    }
    else if (document.all)
    {
        document.all[id].style.visibility = " visible";
    }
    else if (document.layers)
    {
        document.layers[id].style.visibility = " visible";
    }
}






function HidePop(id)
{
       if (document.getElementById)
    {
           document.getElementById(id).style.visibility = " hidden";
    }
    /*else if (document.all)
    {
        document.all[id].style.visibility = " hidden";
    }
    else if (document.layers)
    {
        document.layers[id].style.visibility = " hidden";
    }*/
}



function TogglePop(id)
{
       if (document.getElementById)
    {
        if(document.getElementById(id).style.visibility  == "visible"){
            document.getElementById(id).style.visibility = "hidden";
        }
        else{
            document.getElementById(id).style.visibility  = "visible";
        }
    }
    else if (document.all)
    {
        if(document.all[id].style.visibility  == "visible"){
            document.all[id].style.visibility  = "hidden";
        }
        else{
            document.all[id].style.visibility = "visible";
        }
    }
    else if (document.layers)
    {
        if(document.layers[id].style.visibility == "visible"){
            document.layers[id].style.visibility = "hidden";
        }
        else{
            document.layers[id].style.visibility = "visible";
        }
    }
}


function toggleLayer(whichLayer)
{
    if (document.getElementById)
    {
        // this is the way the standards work
        var style2 = document.getElementById(whichLayer).style;
        style2.display = style2.display? "":"none";
        var link  = document.getElementById(whichLayer+"_").innerHTML;
        if(link.indexOf("(+)") >= 0){
            document.getElementById(whichLayer+"_").innerHTML="(-)"+link.substring(3,link.length);
        }
        else{
            document.getElementById(whichLayer+"_").innerHTML="(+)"+link.substring(3,link.length);
        }
    }//end if
    else if (document.all)
    {
        // this is the way old msie versions work
        var style2 = document.all[whichLayer].style;
        style2.display = style2.display? "":"none";
        var link  = document.all[wwhichLayer+"_"].innerHTML;
        if(link.indexOf("(+)") >= 0){
            document.all[whichLayer+"_"].innerHTML="(-)"+link.substring(3,link.length);
        }
        else{
            document.all[whichLayer+"_"].innerHTML="(+)"+link.substring(3,link.length);
        }
    }
    else if (document.layers)
    {
        // this is the way nn4 works
        var style2 = document.layers[whichLayer].style;
        style2.display = style2.display? "":"none";
        var link  = document.layers[whichLayer+"_"].innerHTML;
        if(link.indexOf("(+)") >= 0){
            document.layers[whichLayer+"_"].innerHTML="(-)"+link.substring(3,link.length);
        }
        else{
            document.layers[whichLayer+"_"].innerHTML="(+)"+link.substring(3,link.length);
        }
    }
}//end function

var checkflag="false";
function check(field) {
  if (checkflag == "false") {
    for (i = 0; i < field.length; i++) {
      field[i].checked = true;
    }
    checkflag = "true";
    return "Uncheck all";
  }
  else {
    for (i = 0; i < field.length; i++) {
      if(field[i].type == 'checkbox'){
        field[i].checked = false;
      }
    }
    checkflag = "false";
    return "Check all";
  }
}

function show_hide_column(tableName, columns) {
    // Let's be clear hear, I have no idea how to write portable
    // JavaScript. This works in Safari, yo.
    var event = window.event;
    var cb = event.target;

    var style = cb.checked ? "table-cell" : "none";

    var tbl  = document.getElementById(tableName);
    var rows = tbl.getElementsByTagName('tr');

    for (var row = 0; row < rows.length; ++row) {
        var cells = rows[row].getElementsByTagName('td');

        if (cells.length == 0)
            cells = rows[row].getElementsByTagName('th');

        for (var i = 0; i < columns.length; ++i)
            cells[columns[i]].style.display = style;
    }
}
