/*** Order Aggregate Report UI ***/

function sum(list) {
    var result = 0.0;
    for (var i = 0; i != list.length; ++i)
        result += list[i];
    return result;
}

function mean(list) {
    if (list.length === 0)
        return 0.0;

    return sum(list) / list.length;
}

/* PlotItem Class */
function PlotItem(graph) {
    this.graph = graph;
    this.oar = graph.oar;
    this.widget = null;
}

PlotItem.prototype.init = function(parent) {
    var graph = this.graph;

    this.widget = $('<div class="oar-plot-item-widget"></div>');
    this.widget.appendTo(parent);

    // Add the plot item header with the plot name.
    var header = $('<div class="oar-plot-item-header"></div>');
    header.appendTo(this.widget);
    header.append("Name:");
    this.plot_name = $('<input type="text" value="Plot">');
    this.plot_name.appendTo(header);
    this.plot_name.change(function() { graph.update_plots(); });

    // Test type selector.
    this.widget.append("Test Type:");
    this.test_type_select = $("<select multiple></select>");
    this.test_type_select.change(function() { graph.update_plots(); });
    this.test_type_select.appendTo(this.widget);
    for (var i in this.oar.data.test_subsets) {
        this.test_type_select.append("<option>" + i + "</option>");
    }

    // Machine selector.
    this.widget.append("<br>");
    this.widget.append("Machines:");
    this.machine_select = $("<select multiple></select>");
    this.machine_select.change(function() { graph.update_plots(); });
    this.machine_select.appendTo(this.widget);
    for (var i = 0; i != this.oar.data.available_machines.length; ++i) {
        var machine = this.oar.data.available_machines[i];
        this.machine_select.append("<option>" + machine[1] + "</option>");
    }

    return this;
}

PlotItem.prototype.compute_plot_info = function() {
    var subsets_to_plot = [];
    var machine_indices_to_plot = [];

    // Create the list of subsets to aggregate over.
    var selected = this.test_type_select[0].selectedIndex;
    var index = 0;
    for (var i in this.oar.data.test_subsets) {
        var option = this.test_type_select[0].options[index];
        if (option.selected || selected == -1)
            subsets_to_plot.push(i);
        index += 1;
    }

    // Create this list of machines to aggregate over.
    selected = this.machine_select[0].selectedIndex;
    for (var i = 0; i != this.machine_select[0].options.length; ++i) {
        var option = this.machine_select[0].options[i];
        if (option.selected || selected == -1) {
            machine_indices_to_plot.push(i);
        }
    }

    return { 'label' : this.plot_name[0].value,
             'subsets_to_plot' : subsets_to_plot,
             'machine_indices_to_plot' : machine_indices_to_plot };
}

/* AggregateGraphWidget Class */
function AggregateGraphWidget(oar) {
    this.oar = oar;
    this.widget = null;
    this.graph_data = null;
    this.plots = null;
    this.plot_items = [];
}

AggregateGraphWidget.prototype.init = function(parent) {
    var agw = this;

    this.widget = $('<div class="oar-graph-widget"></div>');
    this.widget.appendTo(parent);

    // Create the graph element.
    this.graph_elt = $('<div class="oar-graph-element"></div>');
    this.graph_elt.appendTo(this.widget);

    // Create the options UI container element.
    this.options_elt = $('<div class="oar-graph-options"></div>');
    this.options_elt.appendTo(this.widget);

    // Add the global options.
    var options_header = $('<div class="oar-graph-options-header"></div>');
    options_header.appendTo(this.options_elt);

    // Add a button for adding a plot item.
    var add_plot_button = $('<input type="button" value="Add Plot">');
    add_plot_button.appendTo(options_header);
    add_plot_button.click(function () {
        agw.plot_items.push(new PlotItem(agw).init(agw.options_elt));
        agw.update_plots();
    });

    // Add the default plot items.
    this.plot_items.push(new PlotItem(this).init(this.options_elt));

    return this;
}

AggregateGraphWidget.prototype.compute_aggregate_for_run =
    function(subset_name, order_idx, machine_idx)
{
    var test_names = this.oar.data.test_subsets[subset_name];
    var test_data = this.oar.data.data_table[subset_name];
    var pts = []

    for (var i = 0; i != test_names.length; ++i) {
        // Currently we just assume the first machine is the baseline. This
        // needs to get more complicated, eventually.
        var baseline = test_data[test_names[i]][0][machine_idx];
        var value = test_data[test_names[i]][order_idx][machine_idx];
        if (baseline === null || value === null)
            continue;

        // Ignore tests with unreasonable baselines.
        if (baseline < 0.0001)
            continue;

        pts.push((value / baseline - 1.) * 100.);
    }

    return mean(pts);
}

AggregateGraphWidget.prototype.update_plots = function() {
    // First, compute the metadata on the plots we are generating based on the
    // current user options.
    var plot_infos = [];

    for (var i = 0; i != this.plot_items.length; ++i) {
        plot_infos.push(this.plot_items[i].compute_plot_info());
    }

    // For each plot description, compute the plot.
    var orders = this.oar.data.orders_to_aggregate;
    this.plots = [];
    for (var i = 0; i != plot_infos.length; ++i) {
        var info = plot_infos[i];
        var pts = [];

        // Add a point for each run order.
        for (var j = 0; j != orders.length; ++j) {
            var order = parseInt(orders[j]);

            // Compute the aggregate value for each run in this plot.
            var values = [];
            for (var k = 0; k != info.subsets_to_plot.length; ++k) {
                var subset_name = info.subsets_to_plot[k];
                for (var l = 0; l != info.machine_indices_to_plot.length; ++l) {
                    var machine_idx = info.machine_indices_to_plot[l];
                    values.push(this.compute_aggregate_for_run(subset_name, j,
                                                               machine_idx));
                }
            }

            // Compute the final value as the mean of the per-run aggregate.
            var value = mean(values);

            pts.push([order, value]);
        }

        this.plots.push({
            label: info.label,
            data: pts,
            lines: { show: true },
            points: { show: true }});
    }

    // Update the plots.
    var options = {
        series: { lines: { show: true }, shadowSize: 0 },
        zoom: { interactive: true },
        pan: { interactive: true },
        grid: { hoverable: true }
    };
    $.plot(this.graph_elt, this.plots, options);
}

/* OrderAggregateReport Class */

function OrderAggregateReport(ui_elt_name, data) {
    this.ui_elt_name = ui_elt_name;
    this.data = data;
    this.graphs = [];
}

OrderAggregateReport.prototype.init = function() {
    // Initialize the UI  container.
    this.ui_elt = $("#" + this.ui_elt_name);

    // Add a button for adding a graph.
    var oar = this;
    var add_graph_button = $('<input type="button" value="Add Graph">');
    add_graph_button.appendTo(this.ui_elt);
    add_graph_button.click(function () {
        oar.graphs.push(new AggregateGraphWidget(oar).init(oar.ui_elt));
        oar.update_graphs();
    });

    // Add the default graph widget.
    this.graphs.push(new AggregateGraphWidget(this).init(this.ui_elt));

    this.update_graphs();

    return this;
}

OrderAggregateReport.prototype.update_graphs = function() {
    for (var i = 0; i != this.graphs.length; ++i)
        this.graphs[i].update_plots();
}
