from basico import *
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

try:
    from PIL import Image
except ImportError:
    pass

DEFAULT_Y_LABEL = 'volume y'
DEFAULT_X_LABEL = 'volume x'
TITLE_FORMAT_STRING = 'concentrations of "{0}" for each volume at time {1}'


def plot_linear_time_course(data, dm, prefix=None, metab_names=None, shading='gouraud',
                            min_range=np.nan, max_range=np.nan):
    """
    Plots the simulation data on the loaded model assuming that this is in the format
    of an array of compartments as generated by COPASI. This will create a figure for each species

    :param data: timecourse simulation result
    :param dm:   datamodel
    :param prefix: string of compartment prefix to indicate which compartment should be visualized. This is
                   expected to not include the indices, so it would be 'compartment' rather than 'compartment[0]'
    :param metab_names: optional array of metabolite names that should be plotted (defaults to all)
    :param shading: optional shading for the color mesh, defaults to 'gouraud' can also be 'flat'
    :param min_range: optional min range, defaults to NaN, meaning that it is to be the minimum value of the data
    :param max_range: optional max range, defaults to NaN, meaning that it is to be the maximum value of the data

    :return: array with tuple of figures and their axis
    """
    mod = dm.getModel()
    names = [c.getObjectName() for c in mod.getCompartments()]
    if prefix is not None:
        # prefix was specified so filter down to the compartments needed
        names = [c for c in names if c.startswith(prefix + "[")]
    time = data.index.values

    if metab_names is None:
        metab_names = sorted([col[:col.find('{')] for col in data.columns if '{' + names[0] + '}' in col])

    result = []
    for metab in metab_names:
        arr = [data[metab + '{' + c + '}'] for c in names]
        fig, ax = plt.subplots()
        mesh = ax.pcolormesh(time, np.arange(len(names)), arr, shading=shading)
        vmin, vmax = _get_ranges(arr, min_range, max_range)
        mesh.set_clim(vmin=vmin, vmax=vmax)
        fig.colorbar(mesh, ax=ax)
        ax.set_xlabel('time')
        ax.set_ylabel('volume')
        ax.set_title('concentrations of "%s" for each volume' % metab)
        result.append((fig, ax))

    return result


def _split_ranges(names):
    # type: ([str]) -> ([int], [int], [str])
    x_indices = []
    y_indices = []
    prefixes = []
    for name in names:
        first = name.find('[')
        last = name.rfind(']')
        prefix = name[:first]
        if prefix not in prefixes:
            prefixes.append(prefix)
        coords = name[first + 1: last]
        comma = coords.find(',')
        x = int(coords[:comma])
        y = int(coords[comma + 1:])
        if x not in x_indices:
            x_indices.append(x)
        if y not in y_indices:
            y_indices.append(y)

    return x_indices, y_indices, prefixes


def plot_rectangular_time_course(data, dm, times=None, prefix=None, shading='gouraud',
                                 min_range=np.nan, max_range=np.nan):
    """
        Plots the simulation data on the loaded model assuming that this is in the format
        of an array of compartments as generated by COPASI. This will create a figure for each species
        at each of the specified time points.


    :param data: timecourse simulation result
    :param dm:   datamodel
    :param times: optional parameter specifying the times for which to plot the results. If not given, one figure will
                  be created for each output time point in the data
    :param prefix: string of compartment prefix to indicate which compartment should be visualized. This is
                   expected to not include the indices, so it would be 'compartment' rather than 'compartment[0]'
    :param shading: optional shading for the color mesh, defaults to 'gouraud' can also be 'flat'
    :param min_range: optional min range, defaults to NaN, meaning that it is to be the minimum value of the data
    :param max_range: optional max range, defaults to NaN, meaning that it is to be the maximum value of the data

    :return: array with tuple of figures and their axis
    """
    mod = dm.getModel()
    names = [c.getObjectName() for c in mod.getCompartments()]
    x_range, y_range, prefixes = _split_ranges(names)
    time = data.index.values
    if times is None:
        times = time

    if prefix is None:
        prefix = prefixes[0]

    metab_names = sorted([col[:col.find('{')] for col in data.columns if '{' + names[0] + '}' in col])

    result = []
    for i in range(len(data)):
        cur = data.iloc[i]
        t = time[i]
        if t not in times:
            # skip all times we don't need
            continue

        for metab in metab_names:
            arr = _extract_metabolite_data(cur, metab, prefix, x_range, y_range)
            fig, ax = plt.subplots()
            mesh = ax.pcolormesh(x_range, y_range, arr, shading=shading)
            vmin, vmax = _get_ranges(arr, min_range, max_range)
            mesh.set_clim(vmin=vmin, vmax=vmax)
            fig.colorbar(mesh, ax=ax)
            ax.set_xlabel(DEFAULT_X_LABEL)
            ax.set_ylabel(DEFAULT_Y_LABEL)
            ax.set_title(TITLE_FORMAT_STRING.format(metab, t))
            result.append((fig, ax))

    return result


def _extract_metabolite_data(cur, metab, prefix, x_range, y_range):
    num_x = len(x_range)
    num_y = len(y_range)

    arr = np.zeros((num_x, num_y)) * np.nan
    for x in range(num_x):
        for y in range(num_y):
            metab_name = metab + '{' + prefix + '[{0},{1}]'.format(x_range[x], y_range[y]) + '}'
            if metab_name in cur:
                arr[x, y] = cur[metab_name]
    return arr


def animate_rectangular_time_course_as_image(data, dm, metabs=None, prefix=None,
                                             min_range=np.nan, max_range=np.nan, filename=None):
    mod = dm.getModel()
    names = [c.getObjectName() for c in mod.getCompartments()]
    x_range, y_range, prefixes = _split_ranges(names)
    time = data.index.values

    metab_names = sorted([col[:col.find('{')] for col in data.columns if '{' + names[0] + '}' in col])
    if metabs is None:
        metabs = metab_names

    if prefix is None:
        prefix = prefixes[0]

    metab_data = []

    vmax = -np.inf if np.isnan(max_range) else max_range
    vmin = np.inf if np.isnan(min_range) else min_range

    cur = data.iloc[0]
    for i in range(len(metabs)):
        metab = metabs[i]
        arr = _extract_metabolite_data(cur, metab, prefix, x_range, y_range)
        vmin, vmax = _get_ranges(arr, min_range, max_range, vmin, vmax)
        metab_data.append(arr)

    img = _create_image(metab_data, vmax)

    fig, ax = plt.subplots()
    imgplot = ax.imshow(img)
    ax.set_xlabel(DEFAULT_X_LABEL)
    ax.set_ylabel(DEFAULT_Y_LABEL)
    ax.set_title(TITLE_FORMAT_STRING.format(metabs, time[0]))

    def _plot_ith_set(time_index):
        cur = data.iloc[time_index]
        vmax = -np.inf if np.isnan(max_range) else max_range
        vmin = np.inf if np.isnan(min_range) else min_range
        metab_data = []
        for i in range(len(metabs)):
            metab = metabs[i]
            arr = _extract_metabolite_data(cur, metab, prefix, x_range, y_range)
            vmin, vmax = _get_ranges(arr, min_range, max_range, vmin, vmax)
            metab_data.append(arr)

        imgplot.set_data(_create_image(metab_data, vmax))
        ax.set_title(TITLE_FORMAT_STRING.format(metabs, time[time_index]))
        return [imgplot]

    anim = FuncAnimation(
        fig, _plot_ith_set, interval=100, frames=len(time) - 1)

    if filename:
        anim.save(filename)

    return anim


def _create_image(metab_data, vmax):
    img = Image.new('RGB', metab_data[0].shape, color=(73, 109, 137))
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            color = [0, 0, 0]
            for i in range(len(metab_data)):
                color[i] = int(((metab_data[i][x, y] / vmax) * 255))
            img.putpixel((x, y), tuple(color))
    return img


def _get_ranges(arr, min_range=np.nan, max_range=np.nan, vmin=np.inf, vmax=-np.inf):
    vmin = min(vmin, np.min(arr)) if np.isnan(min_range) else min_range
    vmax = max(vmax, np.max(arr)) if np.isnan(max_range) else max_range
    return vmin, vmax


def animate_rectangular_time_course(data, dm, metab=None, prefix=None, shading='gouraud',
                                    min_range=np.nan, max_range=np.nan, filename=None):
    """
        Plots the simulation data on the loaded model assuming that this is in the format
        of an array of compartments as generated by COPASI. This will create a figure for each species
        at each of the specified time points.


    :param data: timecourse simulation result
    :param dm:   datamodel
    :param metab: optional parameter specifying the species to animate. If not given, one the first metab will be chosen
    :param prefix: string of compartment prefix to indicate which compartment should be visualized. This is
                   expected to not include the indices, so it would be 'compartment' rather than 'compartment[0]'
    :param shading: optional shading for the color mesh, defaults to 'gouraud' can also be 'flat'
    :param min_range: optional min range, defaults to NaN, meaning that it is to be the minimum value of the data
    :param max_range: optional max range, defaults to NaN, meaning that it is to be the maximum value of the data
    :param filename: optional filename to a file to which to save the animation to

    :return: the FuncAnimation constructed
    """

    mod = dm.getModel()
    names = [c.getObjectName() for c in mod.getCompartments()]
    x_range, y_range, prefixes = _split_ranges(names)
    time = data.index.values

    metab_names = sorted([col[:col.find('{')] for col in data.columns if '{' + names[0] + '}' in col])
    if metab is None:
        metab = metab_names[0]

    if prefix is None:
        prefix = prefixes[0]

    fig, ax = plt.subplots()
    arr = _extract_metabolite_data(data.iloc[0], metab, prefix, x_range, y_range)
    mesh = ax.pcolormesh(x_range, y_range, arr, shading=shading)
    vmin, vmax = _get_ranges(arr, min_range, max_range)
    mesh.set_clim(vmin=vmin, vmax=vmax)
    fig.colorbar(mesh, ax=ax)
    ax.set_xlabel(DEFAULT_X_LABEL)
    ax.set_ylabel(DEFAULT_Y_LABEL)
    ax.set_title(TITLE_FORMAT_STRING.format(metab, 0))

    def _plot_ith_set(i):
        arr = _extract_metabolite_data(data.iloc[i], metab, prefix, x_range, y_range)
        vmin, vmax = _get_ranges(arr, min_range, max_range)
        mesh.set_array(arr.ravel())
        mesh.set_clim(vmin=vmin, vmax=vmax)
        ax.set_title(TITLE_FORMAT_STRING.format(metab, time[i]))

    anim = FuncAnimation(
        fig, _plot_ith_set, interval=100, frames=len(time) - 1)

    if filename:
        anim.save(filename)

    return anim


# def _get_selection(x_range, y_range):
#     import sys
#     from PyQt5.QtWidgets import QApplication, QGridLayout, QDialog, QPushButton

#     app = QApplication(sys.argv)

#     layout = QGridLayout()

#     w = QDialog()
#     w.resize(250, 150)
#     w.move(300, 300)
#     w.setWindowTitle("Toggle off elements you don't want")

#     buttons = {}

#     for i in x_range:
#         for j in y_range:
#             # keep a reference to the buttons
#             buttons[(i, j)] = QPushButton('.', w)
#             buttons[(i, j)].setCheckable(True)
#             buttons[(i, j)].setMaximumSize(10, 10)
#             # add to the layout
#             layout.addWidget(buttons[(i, j)], i, j)

#     w.setLayout(layout)
#     w.exec()

#     result = []
#     # get selection
#     for coord in buttons:
#         if buttons[coord].isChecked():
#             result.append(coord)
#     return result


# def _delete_compartments(dm):
#     mod = dm.getModel()
#     assert (isinstance(mod, COPASI.CModel))
#     names = [c.getObjectName() for c in mod.getCompartments()]
#     x_range, y_range, prefixes = _split_ranges(names)
#     to_delete = _get_selection(x_range, y_range)
#     delete_compartments(dm, to_delete)


def delete_compartments(dm, selection):
    """
    utility function for deleting a selection of compartments from the datamodel. This will also delete
    the species and reactions included.

    :param dm: the data model
    :param selection: an array of tuples of indices at which the compartments should be deleted
    :return:
    """
    mod = dm.getModel()
    assert (isinstance(mod, COPASI.CModel))
    names = [c.getObjectName() for c in mod.getCompartments()]
    x_range, y_range, prefixes = _split_ranges(names)
    for prefix in prefixes:
        for coord in selection:
            c = mod.getCompartment(prefix + "[" + str(coord[0]) + "," + str(coord[1]) + "]")
            if c is None:
                continue
            key = c.getKey()
            del c
            mod.removeCompartment(key, True)
            mod.forceCompile()


def _create_array(dm, num_steps_x, num_steps_y, linear=True, species=None, diffusion_coefficients=None,
                  compartment_names=None, delete_template=False):
    if not species:
        return
    model = dm.getModel()
    metabs = []
    model_elements = COPASI.CModelExpansion_SetOfModelElements()
    metab_set = COPASI.DataObjectSet()
    keys = []
    names = []

    for name in species:
        metab = dm.findObjectByDisplayName(name)
        if metab is None:
            continue
        metabs.append(metab)
        metab_set.append(metab)
        compartment_name = metab.getCompartment().getObjectName()
        if compartment_names is None:
            compartment_names = [compartment_name]
        names.append('diff_{0}_{1}'.format(compartment_name, metab.getObjectName()))

    for name in compartment_names:
        comp = dm.findObjectByDisplayName(name)
        if comp is None:
            comp = model.getCompartment(name)
            if comp is None:
                continue
        model_elements.addCompartment(comp)
        keys.append(comp.getKey())

    me = COPASI.CModelExpansion(model)
    model_elements.fillDependencies(model)
    if linear:
        me.createLinearArray(model_elements, num_steps_x, metab_set)
    else:
        me.createRectangularArray(model_elements, num_steps_x, num_steps_y, metab_set)

    if delete_template:
        for key in keys:
            model.removeCompartment(key, True)
            model.forceCompile()

    if diffusion_coefficients is not None:
        for i in range(min(len(names), len(diffusion_coefficients))):
            p = model.getModelValue(names[i])
            p.setInitialValue(diffusion_coefficients[i])


def create_linear_array(dm, num_steps, species=None, diffusion_coefficients=None, compartment_names=None,
                        delete_template=False):
    """
    Utility function to create a linear duplicating the specified species, their reactions
    in the given compartments and created diffusion reactions between the newly created array

    :param dm: the model to use
    :param num_steps: the number of steps to create
    :param species: array of species names, that should be diffusing between compartments
    :param compartment_names: optional compartment names (will default to the compartment the species is in)
    :param diffusion_coefficients: optional array of diffusion coefficients in the same order as the species
           (otherwise they will be set to 1)
    :param delete_template: if True, the original template model in the specified compartment will be deleted.
    :return: None
    """
    _create_array(dm, num_steps, 0, linear=True, species=species,
                  compartment_names=compartment_names,
                  diffusion_coefficients=diffusion_coefficients,
                  delete_template=delete_template)


def create_rectangular_array(dm, num_steps_x, num_steps_y, species=None, diffusion_coefficients=None,
                             compartment_names=None, delete_template=False):
    """
    Utility function to create a rectangular array duplicating the specified species, their reactions
    in the given compartments and created diffusion reactions between the newly created array

    :param dm: the model to use
    :param num_steps_x: the number of compartments to create along the x direction
    :param num_steps_y: the number of compartments to create along the y direction
    :param species: array of species names, that should be diffusing between compartments
    :param compartment_names: optional compartment names (will default to the compartment the species is in)
    :param diffusion_coefficients: optional array of diffusion coefficients in the same order as the species
           (otherwise they will be set to 1)
   :param delete_template: if True, the original template model in the specified compartment will be deleted.
    :return: None
    """
    _create_array(dm, num_steps_x, num_steps_y, linear=False, species=species,
                  diffusion_coefficients=diffusion_coefficients,
                  compartment_names=compartment_names,
                  delete_template=delete_template)


if __name__ == "__main__":
    #
    load_example('brusselator')
    set_species('X', initial_concentration=10)
    add_event('E0', 'Time > 10', [['X', '10']])
    data = run_time_course(start_time=0)
    data.plot()
    # open_copasi()
    #
    # create_linear_array(dm, 10, ['X', 'Y'], [0.16, 0.8], delete_template=True)
    # set_species('X{compartment[1]}', initial_concentration=10)
    # data = run_time_course()
    # plot_linear_time_course(data, dm)
    # plt.show()
    # # open_copasi()
    #
    dm = load_example('brusselator')
    create_rectangular_array(dm, 10, 10, ['X', 'Y'], [0.16, 0.8], delete_template=True)
    set_species(['X{compartment[1,1]}',
                 'X{compartment[1,2]}',
                 'X{compartment[2,1]}',
                 'X{compartment[2,2]}'], initial_concentration=10)

    add_event('E0', 'Time > 10', [['X{compartment[1,1]}', '10'],
                                  ['X{compartment[1,2]}', '10'],
                                  ['X{compartment[2,1]}', '10'],
                                  ['X{compartment[2,2]}', '10']])

    data = run_time_course(start_time=0, duration=500)
    # animate_rectangular_time_course(data, dm, "Y", min=0, max=9, filename='bruss_test_500.mp4')
    animate_rectangular_time_course_as_image(data, dm, metabs=["X", "Y"], min_range=0, max_range=10)
    plt.show()
    # # open_copasi()
    # #
    # # print('loading model')
    # # dm = load_example('enzyme_10_lin')
    # # data = run_time_course()
    # # plot_linear_time_course(data, dm)
    # # plt.show()
    # # dm = load_example('brusselator_lin')
    # # dm = load_example('linear_rect')
    # dm = load_example('turing_rect_20')
    # # print('deleting compartments')
    # # _delete_compartments(dm)
    # print('running simulation')
    # data = run_time_course(duration=50)
    # print('creating animation')
    # plot_rectangular_time_course_2(data, dm, times=[10, 90])
    # # animate_rectangular_time_course(data, dm, "S2", min=0, max=1.75)
    # # plot_rectangular_time_course(data, dm, times=[10, 90])
    # plt.show()
