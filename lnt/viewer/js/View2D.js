//===-- View2D.js - HTML5 Canvas Based 2D View/Graph Widget ---------------===//
//
//                     The LLVM Compiler Infrastructure
//
// This file is distributed under the University of Illinois Open Source
// License. See LICENSE.TXT for details.
//
//===----------------------------------------------------------------------===//
//
// This file implements a generic 2D view widget and a 2D graph widget on top of
// it, using the HTML5 Canvas. It currently supports Firefox and Safari
// (Chromium should work, but is untested).
//
// See the Graph2D implementation for details of how to extend the View2D
// object.
//
// FIXME: Currently, this uses MooTools extensions, but I would like to rewrite
// it in pure JS for more portability (e.g., use in Buildbot).
//
//===----------------------------------------------------------------------===//

function lerp(a, b, t) {
    return a * (1.0 - t) + b * t;
}

function clamp(a, lower, upper) {
    return Math.max(lower, Math.min(upper, a));
}

function vec2_neg (a)    { return [-a[0]    , -a[1]    ]; };
function vec2_add (a, b) { return [a[0]+b[0], a[1]+b[1]]; };
function vec2_addN(a, b) { return [a[0]+b   , a[1]+b   ]; };
function vec2_sub (a, b) { return [a[0]-b[0], a[1]-b[1]]; };
function vec2_subN(a, b) { return [a[0]-b   , a[1]-b   ]; };
function vec2_mul (a, b) { return [a[0]*b[0], a[1]*b[1]]; };
function vec2_mulN(a, b) { return [a[0]*b   , a[1]*b   ]; };
function vec2_div (a, b) { return [a[0]/b[0], a[1]/b[1]]; };
function vec2_divN(a, b) { return [a[0]/b   , a[1]/b   ]; };

function vec3_neg (a)    { return [-a[0]    , -a[1]    , -a[2]    ]; };
function vec3_add (a, b) { return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]; };
function vec3_addN(a, b) { return [a[0]+b   , a[1]+b,    a[2]+b   ]; };
function vec3_sub (a, b) { return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]; };
function vec3_subN(a, b) { return [a[0]-b   , a[1]-b,    a[2]-b   ]; };
function vec3_mul (a, b) { return [a[0]*b[0], a[1]*b[1], a[2]*b[2]]; };
function vec3_mulN(a, b) { return [a[0]*b   , a[1]*b,    a[2]*b   ]; };
function vec3_div (a, b) { return [a[0]/b[0], a[1]/b[1], a[2]/b[2]]; };
function vec3_divN(a, b) { return [a[0]/b   , a[1]/b,    a[2]/b   ]; };

function vec2_lerp(a, b, t) {
    return [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];
}
function vec2_mag(a) {
    return a[0] * a[0] + a[1] * a[1];
}
function vec2_len(a) {
    return Math.sqrt(vec2_mag(a));
}

function vec2_floor(a) {
    return [Math.floor(a[0]), Math.floor(a[1])];
}
function vec2_ceil(a) {
    return [Math.ceil(a[0]), Math.ceil(a[1])];
}

function vec3_floor(a) {
    return [Math.floor(a[0]), Math.floor(a[1]), Math.floor(a[2])];
}
function vec3_ceil(a) {
    return [Math.ceil(a[0]), Math.ceil(a[1]), Math.ceil(a[2])];
}

function vec2_log(a) {
    return [Math.log(a[0]), Math.log(a[1])];
}
function vec2_pow(a, b) {
   return [Math.pow(a[0], b[0]), Math.pow(a[1], b[1])];
}
function vec2_Npow(a, b) {
   return [Math.pow(a, b[0]), Math.pow(a, b[1])];
}
function vec2_powN(a, b) {
   return [Math.pow(a[0], b), Math.pow(a[1], b)];
}

function vec2_min(a, b) {
    return [Math.min(a[0], b[0]), Math.min(a[1], b[1])];
}
function vec2_max(a, b) {
    return [Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}
function vec2_clamp(a, lower, upper) {
    return [clamp(a[0], lower[0], upper[0]),
            clamp(a[1], lower[1], upper[1])];
}
function vec2_clampN(a, lower, upper) {
    return [clamp(a[0], lower, upper),
            clamp(a[1], lower, upper)];
}

function vec3_min(a, b) {
    return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.min(a[2], b[2])];
}
function vec3_max(a, b) {
    return [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.max(a[2], b[2])];
}
function vec3_clamp(a, lower, upper) {
    return [clamp(a[0], lower[0], upper[0]),
            clamp(a[1], lower[1], upper[1]),
            clamp(a[2], lower[2], upper[2])];
}
function vec3_clampN(a, lower, upper) {
    return [clamp(a[0], lower, upper),
            clamp(a[1], lower, upper),
            clamp(a[2], lower, upper)];
}

function vec2_cswap(a, swap) {
    if (swap)
        return [a[1],a[0]];
    return a;
}

function col3_to_rgb(col) {
    var norm = vec3_floor(vec3_clampN(vec3_mulN(col, 255), 0, 255));
    return "rgb(" + norm[0] + "," + norm[1] + "," + norm[2] + ")";
}

function col4_to_rgba(col) {
    var norm = vec3_floor(vec3_clampN(vec3_mulN(col, 255), 0, 255));
    return "rgb(" + norm[0] + "," + norm[1] + "," + norm[2] + "," + col[3] + ")";
}

var ViewData = new Class ({
    initialize: function(location, scale) {
        if (!location)
            location = [0, 0];
        if (!scale)
            scale = [1, 1];

        this.location = location;
        this.scale = scale;
    },

    copy: function() {
        return new ViewData(this.location, this.scale);
    },
});

var ViewAction = new Class ({
    initialize: function(mode, v2d, start) {
        this.mode = mode;
        this.start = start;
        this.vd = v2d.viewData.copy();
    },

    update: function(v2d, co) {
        if (this.mode == 'p') {
            var delta = vec2_sub(v2d.convertClientToNDC(co, this.vd),
                v2d.convertClientToNDC(this.start, this.vd))
            v2d.viewData.location = vec2_add(this.vd.location, delta);
        } else {
            var delta = vec2_sub(v2d.convertClientToNDC(co, this.vd),
                v2d.convertClientToNDC(this.start, this.vd))
            v2d.viewData.scale = vec2_Npow(Math.E,
                                           vec2_addN(vec2_log(this.vd.scale),
                                                     delta[1]))
            v2d.viewData.location = vec2_mul(this.vd.location,
                                             vec2_div(v2d.viewData.scale,
                                                      this.vd.scale))
        }

        v2d.refresh();
    },

    complete: function(v2d, co) {
        this.update(v2d, co);
    },

    abort: function(v2d) {
        v2d.viewData = this.vd;
    },
});

var View2D = new Class ({
    initialize: function(canvasname) {
        this.canvasname = canvasname
        this.viewData = new ViewData();
        this.size = [1, 1];
        this.aspect = 1;
        this.registered = false;

        this.viewAction = null;

        this.useWidgets = true;
        this.previewPosition = [5, 5];
        this.previewSize = [60, 60];

        this.clearColor = [1, 1, 1];

        // Bound once registered.
        this.canvas = null;
    },

    registerEvents: function(canvas) {
        if (this.registered)
            return;

        this.registered = true;

        this.canvas = canvas;

        // FIXME: Why do I have to do this?
        var obj = this;

        canvas.addEvent('mousedown', function(event) { obj.onMouseDown(event); })
        canvas.addEvent('mousemove', function(event) { obj.onMouseMove(event); })
        canvas.addEvent('mouseup', function(event) { obj.onMouseUp(event); })
        canvas.addEvent('mousewheel', function(event) { obj.onMouseWheel(event); })

        // FIXME: Capturing!
    },

    onMouseDown: function(event) {
        pos = [event.client.x - this.canvas.offsetLeft,
               this.size[1] - 1 - (event.client.y - this.canvas.offsetTop)];

        if (this.viewAction != null)
            this.viewAction.abort(this);

        if (event.shift)
            this.viewAction = new ViewAction('p', this, pos);
        else if (event.alt || event.meta)
            this.viewAction = new ViewAction('z', this, pos);
        event.stop();
    },
    onMouseMove: function(event) {
        pos = [event.client.x - this.canvas.offsetLeft,
               this.size[1] - 1 - (event.client.y - this.canvas.offsetTop)];

        if (this.viewAction != null)
            this.viewAction.update(this, pos);
        event.stop();
    },
    onMouseUp: function(event) {
        pos = [event.client.x - this.canvas.offsetLeft,
               this.size[1] - 1 - (event.client.y - this.canvas.offsetTop)];

        if (this.viewAction != null)
            this.viewAction.complete(this, pos);
        this.viewAction = null;
        event.stop();
    },
    onMouseWheel: function(event) {
        if (this.viewAction == null) {
            var factor = event.wheel;
            if (event.shift)
                factor *= .1;
            var zoom = 1.0 + .03 * factor;
            this.viewData.location = vec2_mulN(this.viewData.location, zoom);
            this.viewData.scale = vec2_mulN(this.viewData.scale, zoom);
            this.refresh();
        }
        event.stop();
    },

    setViewData: function(vd) {
        // FIXME: Check equality and avoid refresh.
        this.viewData = vd;
        this.refresh();
    },

    refresh: function() {
        // FIXME: Event loop?
        this.draw();
    },

    // Coordinate conversion.

    getAspectScale: function() {
        if (this.aspect > 1) {
            return [1.0 / this.aspect, 1.0];
        } else {
            return [1.0, this.aspect];
        }
    },

    getPixelSize: function() {
        return vec2_sub(this.convertClientToWorld([1,1]),
                        this.convertClientToWorld([0,0]));
    },

    convertClientToNDC: function(pt, vd) {
        if (vd == null)
            vd = this.viewData
        return [pt[0] / this.size[0] * 2 - 1,
                pt[1] / this.size[1] * 2 - 1];
    },

    convertClientToWorld: function(pt, vd) {
        if (vd == null)
            vd = this.viewData
        pt = this.convertClientToNDC(pt, vd)
        pt = vec2_sub(pt, vd.location);
        pt = vec2_div(pt, vec2_mul(vd.scale, this.getAspectScale()));
        return pt;
    },

    convertWorldToPreview: function(pt, pos, size) {
        var asp_scale = this.getAspectScale();
        pt = vec2_mul(pt, asp_scale);
        pt = vec2_addN(pt, 1);
        pt = vec2_mulN(pt, .5);
        pt = vec2_mul(pt, size);
        pt = vec2_add(pt, pos);
        return pt;
    },

    setViewMatrix: function(ctx) {
        ctx.scale(this.size[0], this.size[1]);
        ctx.scale(.5, .5);
        ctx.translate(1, 1);
        ctx.translate(this.viewData.location[0], this.viewData.location[1]);
        var scale = vec2_mul(this.viewData.scale, this.getAspectScale());
        ctx.scale(scale[0], scale[1]);
    },

    setPreviewMatrix: function(ctx, pos, size) {
        ctx.translate(pos[0], pos[1]);
        ctx.scale(size[0], size[1]);
        ctx.scale(.5, .5);
        ctx.translate(1, 1);
        var scale = this.getAspectScale();
        ctx.scale(scale[0], scale[1]);
    },

    setWindowMatrix: function(ctx) {
        ctx.translate(.5, .5);
        ctx.translate(0, this.size[1]);
        ctx.scale(1, -1);
    },

    draw: function() {
        var canvas = document.getElementById(this.canvasname);
        var ctx = canvas.getContext("2d");

        this.registerEvents(canvas);

        if (canvas.width != this.size[0] || canvas.height != this.size[1]) {
            this.size = [canvas.width, canvas.height];
            this.aspect = canvas.width / canvas.height;
            this.previewPosition[0] = this.size[0] - this.previewSize[0] - 5;
            this.on_size_change();
        }

        this.on_draw_start();

        ctx.save();

        // Clear and draw the view content.
        ctx.save();
        this.setWindowMatrix(ctx);

        ctx.clearRect(0, 0, this.size[0], this.size[1]);
        ctx.fillStyle = col3_to_rgb(this.clearColor);
        ctx.fillRect(0, 0, this.size[0], this.size[1]);

        this.setViewMatrix(ctx);
        this.on_draw(canvas, ctx);
        ctx.restore();

        if (this.useWidgets)
            this.drawPreview(canvas, ctx)

        ctx.restore();
    },

    drawPreview: function(canvas, ctx) {
        // Setup the preview context.
        this.setWindowMatrix(ctx);

        // Draw the preview area outline.
        ctx.fillStyle = "rgba(128,128,128,.5)";
        ctx.fillRect(this.previewPosition[0]-1, this.previewPosition[1]-1,
                     this.previewSize[0]+2, this.previewSize[1]+2);
        ctx.lineWidth = 1;
        ctx.strokeStyle = "rgb(0,0,0)";
        ctx.strokeRect(this.previewPosition[0]-1, this.previewPosition[1]-1,
                       this.previewSize[0]+2, this.previewSize[1]+2);

        // Compute the aspect corrected preview area.
        var pv_size = [this.previewSize[0], this.previewSize[1]];
        if (this.aspect > 1) {
            pv_size[1] /= this.aspect;
        } else {
            pv_size[0] *= this.aspect;
        }
        var pv_pos = vec2_add(this.previewPosition,
            vec2_mulN(vec2_sub(this.previewSize, pv_size), .5));

        // Draw the preview, making sure to clip to the proper area.
        ctx.save();
        ctx.beginPath();
        ctx.rect(pv_pos[0], pv_pos[1], pv_size[0], pv_size[1]);
        ctx.clip();
        ctx.closePath();

        this.setPreviewMatrix(ctx, pv_pos, pv_size);
        this.on_draw_preview(canvas, ctx);
        ctx.restore();

        // Draw the current view overlay.
        //
        // FIXME: Find a replacement for stippling.
        ll = this.convertClientToWorld([0, 0])
        ur = this.convertClientToWorld(this.size);

        // Convert to pixel coordinates instead of drawing in content
        // perspective.
        ll = vec2_floor(this.convertWorldToPreview(ll, pv_pos, pv_size))
        ur = vec2_ceil(this.convertWorldToPreview(ur, pv_pos, pv_size))
        ll = vec2_clamp(ll, this.previewPosition,
                        vec2_add(this.previewPosition, this.previewSize))
        ur = vec2_clamp(ur, this.previewPosition,
                        vec2_add(this.previewPosition, this.previewSize))

        ctx.strokeStyle = "rgba(128,128,128,255)";
        ctx.lineWidth = 1;
        ctx.strokeRect(ll[0], ll[1], ur[0] - ll[0], ur[1] - ll[1]);
    },

    on_size_change: function() {},
    on_draw_start: function() {},
    on_draw: function(canvas, ctx) {},
    on_draw_preview: function(canvas, ctx) {},
});

var View2DTest = new Class ({
    Extends: View2D,

    on_draw: function(canvas, ctx) {
        ctx.fillStyle = "rgb(255,255,255)";
        ctx.fillRect(-1000, -1000, 2000, 20000);

        ctx.lineWidth = .01;
        ctx.strokeTyle = "rgb(0,200,0)";
        ctx.strokeRect(-1, -1, 2, 2);

        ctx.fillStyle = "rgb(200,0,0)";
        ctx.fillRect(-.8, -.8, 1, 1);

        ctx.fillStyle = "rgb(0,0,200)";
        ctx.beginPath();
        ctx.arc(0, 0, .5, 0, 2 * Math.PI, false);
        ctx.fill();
        ctx.closePath();
    },

    on_draw_preview: function(canvas, ctx) {
        ctx.fillStyle = "rgba(255,255,255,.4)";
        ctx.fillRect(-1000, -1000, 2000, 20000);

        ctx.lineWidth = .01;
        ctx.strokeTyle = "rgba(0,200,0,.4)";
        ctx.strokeRect(-1, -1, 2, 2);

        ctx.fillStyle = "rgba(200,0,0,.4)";
        ctx.fillRect(-.8, -.8, 1, 1);

        ctx.fillStyle = "rgba(0,0,200,.4)";
        ctx.beginPath();
        ctx.arc(0, 0, .5, 0, 2 * Math.PI, false);
        ctx.fill();
        ctx.closePath();
    },
});

var Graph2D_GraphInfo = new Class ({
    initialize: function() {
        this.xAxisH = 0;
        this.yAxisW = 0;
        this.ll = [0, 0];
        this.ur = [1, 1];
    },

    toNDC: function(pt) {
        return [2 * (pt[0] - this.ll[0]) / (this.ur[0] - this.ll[0]) - 1,
                2 * (pt[1] - this.ll[1]) / (this.ur[1] - this.ll[1]) - 1];
    },

    fromNDC: function(pt) {
        return [this.ll[0] + (this.ur[0] - this.ll[0]) * (pt[0] + 1) * .5,
                this.ll[1] + (this.ur[1] - this.ll[1]) * (pt[1] + 1) * .5];
    },
});

var Graph2D_PlotStyle = new Class ({
    initialize: function() {},

    plot: function(graph, ctx, data) {},
});

var Graph2D_LinePlotStyle = new Class ({
    Extends: Graph2D_PlotStyle,

    initialize: function(width, color) {
        if (!width)
            width = 1;
        if (!color)
            color = [0,0,0];

        this.parent();
        this.width = width;
        this.color = color;
    },

    plot: function(graph, ctx, data) {
        if (data.length === 0)
            return;

        ctx.beginPath();
        var co = graph.graphInfo.toNDC(data[0]);
        ctx.moveTo(co[0], co[1]);
        for (var i = 1, e = data.length; i != e; ++i) {
            var co = graph.graphInfo.toNDC(data[i]);
            ctx.lineTo(co[0], co[1]);
        }
        ctx.lineWidth = this.width * (graph.getPixelSize()[0] + graph.getPixelSize()[1]) * .5;
        ctx.strokeStyle = col3_to_rgb(this.color);
        ctx.stroke();
    },
});

var Graph2D_Axis = new Class ({
    // Static Methods
    formats: {
        normal: function(value, iDigits, fDigits) {
            // FIXME: iDigits?
            return value.toFixed(fDigits);
        },
        day: function(value, iDigits, fDigits) {
            var date = new Date(value * 1000.);
            var res = date.getUTCFullYear();
            res += "-" + (date.getUTCMonth() + 1);
            res += "-" + (date.getUTCDate() + 1);
            return res;
        },
    },

    initialize: function(dir, format) {
        if (!format)
            format = this.formats.normal;

        this.dir = dir;
        this.format = format;
    },

    draw: function(graph, ctx, ll, ur, mainUR) {
        var dir = this.dir, ndir = 1 - this.dir;
        var vMin = ll[dir];
        var vMax = ur[dir];
        var near = ll[ndir];
        var far = ur[ndir];
        var border = mainUR[ndir];

        var line_base = (graph.getPixelSize()[0] + graph.getPixelSize()[1]) * .5;
        ctx.lineWidth = 2 * line_base;
        ctx.strokeStyle = "rgb(0,0,0)";

        ctx.beginPath();
        var co = vec2_cswap([vMin, far], dir);
        co = graph.graphInfo.toNDC(co);
        ctx.moveTo(co[0], co[1]);
        var co = vec2_cswap([vMax, far], dir);
        co = graph.graphInfo.toNDC(co);
        ctx.lineTo(co[0], co[1]);
        ctx.stroke();

        var delta = vMax - vMin;
        var steps = Math.floor(Math.log(delta) / Math.log(10));
        if (delta / Math.pow(10, steps) >= 5.0) {
            var size = .5;
        } else if (delta / Math.pow(10, steps) >= 2.5) {
            var size = .25;
        } else {
            var size = .1;
        }
        size *= Math.pow(10, steps);

        if (steps <= 0) {
            var iDigits = 0, fDigits = 1 + Math.abs(steps);
        } else {
            var iDigits = steps, fDigits = 0;
        }

        var start = Math.ceil(vMin / size);
        var end = Math.ceil(vMax / size);

        // FIXME: Draw in window coordinates to make crisper.

        // FIXME: Draw grid in layers to avoid ugly overlaps.

        for (var i = start; i != end; ++i) {
            if (i == 0) {
                ctx.lineWidth = 3 * line_base;
                var p = .5;
            } else if (!(i & 1)) {
                ctx.lineWidth = 2 * line_base;
                var p = .5;
            } else {
                ctx.lineWidth = 1 * line_base;
                var p = .75;
            }

            ctx.beginPath();
            var co = vec2_cswap([i * size, lerp(near, far, p)], dir);
            co = graph.graphInfo.toNDC(co);
            ctx.moveTo(co[0], co[1]);
            var co = vec2_cswap([i * size, far], dir);
            co = graph.graphInfo.toNDC(co);
            ctx.lineTo(co[0], co[1]);
            ctx.stroke();
        }

        for (var alt = 0; alt < 2; ++alt) {
            if (alt)
                ctx.strokeStyle = "rgba(190,190,190,.5)";
            else
                ctx.strokeStyle = "rgba(128,128,128,.5)";
            ctx.lineWidth = 1 * line_base;
            ctx.beginPath();
            for (var i = start; i != end; ++i) {
                if (i == 0)
                    continue;
                if ((i & 1) == alt) {
                    var co = vec2_cswap([i * size, far], dir);
                    co = graph.graphInfo.toNDC(co);
                    ctx.moveTo(co[0], co[1]);
                    var co = vec2_cswap([i * size, border], dir);
                    co = graph.graphInfo.toNDC(co);
                    ctx.lineTo(co[0], co[1]);
                }
            }
            ctx.stroke();

            if (start <= 0 && 0 < end) {
                ctx.beginPath();
                var co = vec2_cswap([0, far], dir);
                co = graph.graphInfo.toNDC(co);
                ctx.moveTo(co[0], co[1]);
                var co = vec2_cswap([0, border], dir);
                co = graph.graphInfo.toNDC(co);
                ctx.lineTo(co[0], co[1]);
                ctx.strokeStyle = "rgba(64,64,64,.5)";
                ctx.lineWidth = 3 * line_base;
                ctx.stroke();
            }
        }

        // FIXME: Draw this in screen coordinates, and stop being stupid. Also,
        // figure out font height?
        if (this.dir == 1) {
            var offset = [-.5, -.25];
        } else {
            var offset = [-.5, 1.1];
        }
        ctx.fillStyle = "rgb(0,0,0)";
        var pxl = graph.getPixelSize();
        for (var i = start; i != end; ++i) {
            if ((i & 1) == 0) {
                var label = this.format(i * size, iDigits, fDigits);
                ctx.save();
                var co = vec2_cswap([i*size, lerp(near, far, .5)], dir);
                co = graph.graphInfo.toNDC(co);
                ctx.translate(co[0], co[1]);
                ctx.scale(pxl[0], -pxl[1]);
                // FIXME: Abstract.
                var bb_w = label.length * 5;
                if (ctx.measureText != null)
                    bb_w = ctx.measureText(label).width;
                var bb_h = 12;
                // FIXME: Abstract? Or ignore.
                if (ctx.fillText != null) {
                    ctx.fillText(label, bb_w*offset[0], bb_h*offset[1]);
                } else if (ctx.mozDrawText != null) {
                    ctx.translate(bb_w*offset[0], bb_h*offset[1]);
                    ctx.mozDrawText(label);
                }
                ctx.restore();
            }
        }
    },
});

var Graph2D = new Class ({
    Extends: View2D,

    initialize: function(canvasname) {
        this.parent(canvasname);

        this.useWidgets = false;
        this.plots = [];
        this.graphInfo = null;
        this.xAxis = new Graph2D_Axis(0);
        this.yAxis = new Graph2D_Axis(1);
        this.debugText = null;

        this.clearColor = [.8, .8, .8];
    },

    //

    graphChanged: function() {
        this.graphInfo = null;
        // FIXME: Need event loop.
        this.refresh();
    },

    layoutGraph: function() {
        var gi = new Graph2D_GraphInfo();

        gi.xAxisH = 40;
        gi.yAxisW = 40;

        var min = null, max = null;
        for (var i = 0, e = this.plots.length; i != e; ++i) {
            var data = this.plots[i][0];
            for (var i2 = 0, e2 = data.length; i2 != e2; ++i2) {
                if (min == null)
                    min = data[i2];
                else
                    min = vec2_min(min, data[i2]);

                if (max == null)
                    max = data[i2];
                else
                    max = vec2_max(max, data[i2]);
            }
        }

        if (min === null)
            min = [0, 0];
        if (max === null)
            max = [0, 0];
        if (Math.abs(max[0] - min[0]) < .001)
            max[0] += 1;
        if (Math.abs(max[1] - min[1]) < .001)
            max[1] += 1;

        // Set graph transform to the [min,max] rect to the content area with
        // some padding.
        //
        // FIXME: Add real mat3 and implement this properly.
        var pad = 5;
        var vd = new ViewData();
        var ll_target = this.convertClientToWorld([gi.yAxisW + pad, gi.xAxisH + pad], vd);
        var ur_target = this.convertClientToWorld(vec2_subN(this.size, pad), vd);
        var target_size = vec2_sub(ur_target, ll_target);
        var target_center = vec2_add(ll_target, vec2_mulN(target_size, .5));

        var center = vec2_mulN(vec2_add(min, max), .5);
        var size = vec2_sub(max, min);

        var scale = vec2_mulN(target_size, .5);
        size = vec2_div(size, scale);
        center = vec2_sub(center, vec2_mulN(vec2_mul(target_center, size), .5));

        gi.ll = vec2_sub(center, vec2_mulN(size, .5));
        gi.ur = vec2_add(center, vec2_mulN(size, .5));

        return gi;
    },

    //

    convertClientToGraph: function(pt) {
        return this.graphInfo.fromNDC(this.convertClientToWorld(pt));
    },

    //

    on_size_change: function() {
        this.graphInfo = null;
    },

    on_draw_start: function() {
        if (!this.graphInfo)
            this.graphInfo = this.layoutGraph();
    },

    on_draw: function(canvas, ctx) {
        var gi = this.graphInfo;
        var w = this.size[0], h = this.size[1];

        this.xAxis.draw(this, ctx,
                        this.convertClientToGraph([gi.yAxisW, 0]),
                        this.convertClientToGraph([w, gi.xAxisH]),
                        this.convertClientToGraph([w, h]))
        this.yAxis.draw(this, ctx,
                        this.convertClientToGraph([0, gi.xAxisH]),
                        this.convertClientToGraph([gi.yAxisW, h]),
                        this.convertClientToGraph([w, h]))

        if (this.debugText != null) {
            ctx.save();
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.fillText(this.debugText, this.size[0]/2 + 10, this.size[1]/2 + 10);
            ctx.restore();
        }

        // Draw the contents.
        ctx.save();
        ctx.beginPath();
        var content_ll = this.convertClientToWorld([gi.yAxisW, gi.xAxisH]);
        var content_ur = this.convertClientToWorld(this.size);
        ctx.rect(content_ll[0], content_ll[1],
                 content_ur[0]-content_ll[0], content_ur[1]-content_ll[1]);
        ctx.clip();

        for (var i = 0, e = this.plots.length; i != e; ++i) {
            var data = this.plots[i][0];
            var style = this.plots[i][1];
            style.plot(this, ctx, data);
        }
        ctx.restore();
    },

    // Client API.

    clearPlots: function() {
        this.plots = [];
        this.graphChanged();
    },

    addPlot: function(data, style) {
        if (!style)
            style = new Graph2D_LinePlotStyle(1);
        this.plots.push( [data, style] );
        this.graphChanged();
    },
});
