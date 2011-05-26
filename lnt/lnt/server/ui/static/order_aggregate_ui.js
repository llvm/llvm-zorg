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

/* AggregateGraphWidget Class */
function AggregateGraphWidget(oar, name) {
    this.oar = oar;
    this.name = name;
    this.widget = null;
    this.graph_data = null;
    this.plots = null;
}

AggregateGraphWidget.prototype.init = function(parent) {
    this.widget = $('<div class="oar_graph_widget"></div>');
    this.widget.prependTo(parent);

    // Create the graph element.
    this.graph_elt = $('<div id="' + this.name + '.plot" ' +
                            'style="width:400px;height:300px;"></div>');
    this.graph_elt.appendTo(this.widget);
}

AggregateGraphWidget.prototype.compute_aggregate_for_run =
    function(subset_name, order_idx, machine_idx)
{
    var test_names = this.oar.data.test_subsets[subset_name];
    var test_data = this.oar.data.data_table[subset_name];
    var pts = []

    for (var i = 0; i != test_names.length; ++i) {
        var baseline = test_data[test_names[i]][0][machine_idx];
        var value = test_data[test_names[i]][order_idx][machine_idx];
        if (baseline === null || value === null)
            continue;

        pts.push(value / baseline);
    }

    console.log([subset_name, order_idx, machine_idx, pts]);

    return mean(pts);
}

AggregateGraphWidget.prototype.compute_plots = function() {
    // First, compute the metadata on the plots we are generating based on the
    // current user options.
    var plot_infos = [{ 'subsets_to_plot' : ["Compile Time"],
                        'machine_indices_to_plot' : [1] },
                      { 'subsets_to_plot' : ["Execution Time"],
                        'machine_indices_to_plot' : [1] }];


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
            label: "Plot " + (i+1).toString(),
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
}

OrderAggregateReport.prototype.init = function() {
    // Initialize the UI  container.
    this.ui_elt = $("#" + this.ui_elt_name);

    // Add the default graph widget.
    var widget = new AggregateGraphWidget(this, "oar_graph_widget");
    widget.init(this.ui_elt);
    widget.compute_plots();

    return this;
}
