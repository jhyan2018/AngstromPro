AngstromPro is a program that allows the use to perform data analysis and image processing on various forms of STM data. The paper related to this program can be found at www.doi:.... This paper gives more details on the mathematics behind the each of the functions.
# Settings and Package Installation
Before running the GuiVarManager.py, you need to change some settings and install packages. I recommend using Spyder 6.0.7, which can be launched through Anaconda, a popular platform for Python programming. All the settings and packages are based on Spyder, ensuring a seamless development experience.
### iOS 
- Step 0: find your preferences settings page of Spyder
    For Mac, just choose Python ->Preferences 
- Step 1: 
    Run -> General settings
    For Mac: Choose “Run in console’s namespace instead of an empty one”
- Step 2:
    In Preferences, choose the IPython console -> click the Startup tab. 
    In Run a file: Tick “Use the following file” and select the initMagic.py file in your Angstrom Pro folder
- Step 3: optional, do it when canvas looks weird
    Adjust dpi for canvas to fit your computer:
	    -Find the file: SinceY/GUI/ImageUdsData2or3DWidget.py
	    -Adjust dpi value for canvas: `self.static_canvas = QtMatplotCanvas(Figure(figsize=(10, 10), dpi = 100))
	    Change the dpi value in line 78 to fit your computer or remove the “#” in line 76, 77, and 78
	    Do same operation @ SinceY/GUI/Plot1DWidget.py
- Step 4:
    Install packages:
        Run the following command in your Spyder console:
            ``pip install imageio
            ``pip install "imageio[ffmpeg]"
            ``pip install ctypes
- Step 5:
    Ensure the config file is correct in the folder

- Step 6:
    Open GuiVarManager.py in spyder and run it.

### Windows
- Step 0: find your preferences settings page
    For Windows, choose Tool->Preferences
- Step 1: 
    Run -> General settings
    For Windows: Click on each files extension and click the pen.  Choose “Run in console’s namespace instead of an empty one”. 
- Step 2:
    In Preferences, choose the IPython console -> click the Startup tab. 
    In 'Run a file': Tick “Use the following file” and select the initMagic.py file in your Angstrom Pro folder
- Step 3: optional, do it when canvas looks weird
    Adjust dpi for canvas to fit your computer:
	    Find the file: SinceY/GUI/ImageUdsData2or3DWidget.py
	    Adjust dpi value for canvas: 
	    `self.static_canvas = QtMatplotCanvas(Figure(figsize=(10, 10), dpi = 100))`  
	    Change the dpi value in line 78 to fit your computer or remove the “#” in line 76, 77, and 78
	    Do same operation @ SinceY/GUI/Plot1DWidget.py
- Step 4:
    Install packages:
        Run the following command in your Spyder console:
            ``pip install imageio
            ``pip install "imageio[ffmpeg]"
            ``pip install ctypes
- Step 5:
    Ensure the config file is correct in the folder
- Step 6:
    Open GuiVarManager.py in spyder and run it.

# How to Use Angstrom Pro
The menu bar has 4 menus to choose from. 
## File: 
This managed the files from Windows Explorer
- Load from file: 
	- Loads files from windows explorer to the USD Variables for use in the program. 
	- The file types that can be uploaded are .uds, .3ds, .sxm, .dat, .tfr, .1fl, .txt, .npy, .mat. All files uploaded will be then separated into the different channels depending on the type of data uploaded
- Save to file:
	- Save the file currently selected in USD Variables. This will then launch windows explorer to allow you to save in a specific folder and change the file name.

To rename a file in USD Variables, double click an UDS variable in the list the name of the UDS variable will appear in the text box to the right of the “Rename” button. The button will then become active. You then modify the name in the text box, and then click the “Rename” button to save the modified name. 

To delete a variable from the USD variables list, you must click the lock/unlock button beneath the USD variable list. This will then activate the “Remove Var” button. You can then select the variable you list to want to remove and select the “Remove Var” button and the variable will be removed from the list. 
## Edit: 
This is currently blank. #unfinished 
## Modules: 
This allows you to add a new module in the Alive Modules section. 
	The list of modules includes
		[[#Data Browser]]
		[[#Image2U3]]
		[[#Plot1U2]]
		[[#RtSynthesis2D]]
The first 3 modules open in the Alive Modules list as default

To delete a module from Alive Modules list, you must click the lock/unlock button beneath the USD variable list. This will then activate the “Remove” button. You can then select the variable you list to want to remove and select the “Remove” button and the variable will be removed from the list.
## Option: 
### Preference: 
You can change the data path that the program uses. 
	This opens a side widow on the left. This can be minimized or closed. 
	A small window is given to show the current data path. 
	To change the data path you can either
	- Type in or paste the data path directly into the box, or
	- Click the “C” button that opens the Windows Explorer and allows you to navigate to the correct folder.
	 - You must click save afterward to save the changes. 

### About: 
 This gives details about the program
# Variable Handling

There are two types of variable lists being handled by the program.
### Global Variables
These variables are handled by the program outside of the individual modules. 
You can upload these modules to the USD variable list using the [[#File]] menu. 
Once a file is uploaded to the Global Variables list, they can be sent to the module using the "-> Send ->" button. It then can be used as a local variable.. If a variable is deleted from the global variable list, it cannot be accessed by a module. 
### Local Variables
Local Variables are used by each of the modules and are copies of the Global Variable. 
When a module acts on the local variable, a new version of that variable is created in the local variable list with a [[#Suffix]] added to show what process has been acted on it. 
# Modules
## Data Browser
The Data Browser supports a wide range of file formats and adapts its snapshot rendering strategy to the data structure, such as displaying 2D images or multiple curves depending on the file content. 
The window is split into 2 sections. The Docked Widget on the left and the Gallery on the right.
### Docked widget: 
This widget has two tabs on the bottom left, Channels and Files. 
#### Channels:
- View: This allows you to choose to see 2 or 3 plots in a row. 
- Channel Filter: Most STM data has multiple different types of data and you can select which type you want to view in the gallery. 
#### Files:
- Data Path: This allows you to set the data path to allow browsing easier. Clicking on the folder populates the gallery with snapshots of files matching the format filter.
- Format Filter: This filers the files in the data to allow you to only see relevant files. You must write the file type as "* . ---"
### Gallery:  
Here you can see a snapshot of all files in a gallery. Additional blocks provide basic file information and interactive options, such as sending corresponding data to the Global Variable List for further processing.
 - To optimize memory usage, only snapshots currently in view are loaded, while out-of-view snapshots are dynamically discarded. With these features, the Data Browser provides powerful and intuitive tool for efficiently browsing, organizing and exploring enormous and diverse datasets.
## Image2U3 (Multiple 2D Images Visualizer & Analyzer)
Multiple 2D Images Visualizer & Analyzer module. When opened you are immediately shown an empty Var Dock Widget on the left, and two blank [[#Main]] and [[#Auxiliary]] images.  
### Var Dock Widget
#### Local Var List
This is a list of the [[#Local Variables]] used by the modules. To view the a Local Variable in the Main section, double click on the files name. The fast Fourier transform will be automatically generated in the Auxiliary. 
##### Prefixes
- It will get the prefix "m" if this current local variable is being viewed by the [[Main]] section
- It will get the prefix "s" if this current local variable is being viewed by the [[Auxiliary]] section
- It will get the prefix "ms" if this current local variable is being viewed by both the [[Main]] section and the [[Auxiliary]] section
##### Suffixes
Suffixes are added as new processes are conducted on each variable. This helps you keep track of that processes that have been enacted on the data file. 

| Suffix | Process                  	    |
| ------ | ---------------------------------|
| fft    | [[#Fourier Transform]]   	    |
| bg     | [[#Background Subtract]] 	    |
| cp     | [[#Crop Region]]         	    |
| pl     | [[#Perfect Lattice]]     	    |
| df     | [[#Displacement Field]]  	    |
| lf     | [[#Lawler-Fujita Correlation]]   |
| fo     | [[#Fourier Filter Out]]          |
| fi     | [[#Fourier Filter Isolate]]      |
| amp    | [[#Amplitude Map]]               |
| pha    | [[#Phase Map]]                   |
| mat    | [[#Math ]]                       |
| rmp    | [[#Resistance Map]]              |
| gm     | [[#Gap Map]]                     |
| rg     | [[#Registered ]]                 |
| sxcorr | [[#Statistic Cross Correlation]] |
| xcorr  | [[#Cross Correlation]]           |
| ?l     | [[#Extracted ?th Layer]]         |
| itg    | [[#Integral ]]                   |
| nmz    | [[#Normalization ]]              |
| lcr    | [[#Line Cut along R-axis]]       |
| lce    | [[#Line Cut along E-axis]]       |
| lcv    | [[#Line Cut along E vs R]]       |
| cc     | [[#Circle Cut]]                  |
| pd     | [[#Padding ]]                    |
| ip     | [[#Interpolation ]]              |
| ?fs    | [[#? Fold Symmetrize]]           |
| err    | [[#Error Occur]]                 |
#### Remove Variable
The "Remove Variable" button will delete the selected variable from the Local Var List. 
When a variable has been deleted, there is no way to restore this variable. 
#### <- Send <-
This sends the selected Local Variable back to the Global variable list. From there they can be saved or sent into a different module.  
#### Process History
This give a chronological list of all processes that have been conducted on this variable.
### Main 
This is the data that is selected from the Local Var List. 
#### Image
This shows the 2D image of the data
#### Color Scale
From here you can edit color scale of the image.
The maximum and minimum values of the color scale are shown in the top and bottom boxes, respectively, where they can be copied to clipboard if needed.
For FFT images, the upper color scale limit is by default set to a × max(data), where a is the value defined in [[Preferences → Main & Auxiliary → FFT image auto scale]].The default value of a = 0.5, and it can be adjusted by the user within the range (0, 1).
For non-FFT data, the default color scale limits are set to mean ± b$\sigma$, where $\sigma$ is obtained from a Gaussian fit of the data and b = 5 by default. The value of b can be modified in the box next to the $\sigma$ icon. 
The $\sigma$ icon is enabled by default and appears in blue when active. Clicking this icon deactivates $\sigma$-scaling, in which case the color scale limits for non-FFT data revert to the actual maximum and minimum values in the dataset.
Users may also manually adjust the color scale by dragging the red/blue handles on the color bar or by directly editing the values in the top and bottom boxes.
- F: (Full scale) Reset the color scale to full scale
- o: (Zoom out) Expand the adjustable range of the red/blue handles on the color bar.
- i: (Zoom in) Shrink the adjustable range of the red/blue handles on the color bar.
#### Palette
This allows you to change the color palette of the image. You can change the selection of the different palettes using the [[#ColorMap]] menu in the [[#Options Menu]] under preferences. 
#### Picked Points
This shows you the co-ordinates of the points that you have picked on the image. You can pick the points by using your cursor and right-clicking on the pixel. 
You can change the color of the points that you have picked using the drop down menu. 
You can remove the points you have selected by selecting the point in the list and clicking "Remove Point" 
#### Params
This is the text box where you can input the parameters required for the processes and analysis functions that the program can preform. 
#### Information
- Select Variable: allows you to select a variable on the Local Var List to be displayed. 
- Name: Gives the name of the data
- Type: Controls how complex-valued data are displayed. Since all data in AngstromPro are treated as complex numbers, this option selects which component is visualized — the magnitude (abs), phase (angle), real part (real), or imaginary part (imag) — depending on the analysis need.
- Layer: You can change the layer of the data that you are looking at with 3D data. It give the layer index and the energy value. 
- Data Coords: This gives the co-ordinates of the data your cursor is over in the image and it give the value at that data point. 
- Info: This give the necessary metadata for the image currently being displayed. 
### Auxiliary
#### Image
This shows the 2D image of the data
#### Color Scale
From here you can edit color scale of the image
The maximum and minimum data shown in the data. The max value is given in the top box and the minimum value is given in the bottom box. You can copy them from here to paste where needed. 
$\sigma$ is the standard deviations from the mean. It is set to 5 as default. You can edit this value. To unselect it, click the $\sigma$ button.  
- F: (Full scale) Reset the color scale to full scale
- o: (Zoom out) Expand the adjustable range of the red/blue handles on the color bar.
- i: (Zoom in) Shrink the adjustable range of the red/blue handles on the color bar.
#### Palette
This allows you to change the color palette of the image. You can change the selection of the different palettes using the [[#ColorMap]] menu in the [[#Options Menu]] under preferences. 
#### Picked Points
This shows you the co-ordinates of the points that you have picked on the image. You can pick the points by using your cursor and right-clicking on the pixel. 
You can change the color of the points that you have picked using the drop down menu. 
You can remove the points you have selected by selecting the point in the list and clicking "Remove Point" 
#### Params
This is the text box where you can input the parameters required for the processes and analysis functions that the program can preform. 
#### Information
- Select Variable: allows you to select a variable on the Local Var List to be displayed. 
- Name: Gives the name of the data
- Type: Controls how complex-valued data are displayed. Since all data in AngstromPro are treated as complex numbers, this option selects which component is visualized — the magnitude (abs), phase (angle), real part (real), or imaginary part (imag) — depending on the analysis need.
- Layer: You can change the layer of the data that you are looking at with 3D data. It give the layer index and the energy value. 
- Data Coords: This gives the co-ordinates of the data your cursor is over in the image and it give the value at that data point. 
- Info: This give the necessary metadata for the image currently being displayed.  
### File Menu
#### Export
This exports either the Main or Auxiliary as a PNG image to be saved locally or be copied to the clipboard.  
#### Make Movie From
Multi-dimensional data can also be exported as an .mp4 files with each layer serving as a frame. 
### Process Menu
*Note: All data processing operations are applied to all layers of the 3D data, except for [[#Line Cut]],[[#Circle Cut]],[[#Extract one Layer]] and [[#Integral]]*
#### Background Subtract
This process can help remove a slope from the image that is caused by the angle of the sample relative to the tip of the STM. This will leave behind only the atomic resolution. All backgrounds are calculated using least square fitting. 
There are two functions that are used:
##### 2D subtraction
This fits a first order 2D plane to the image and subtract that plane from the image.
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters:
- Order: int, optional
	- Specify the order of the fitting. 
	- *Default: 1*
##### Line-By-Line Subtraction
This fits a curve to each horizonal line of the image and subtracts that from the image. 
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters:
- Order: int, optional
	- Specify the order of the fitting. 
	- *Default: 1*
#### Crop Region
Select 2 points by right clicking on the Main image. These points should be the top left/bottom right or top right/bottom left corners of the what you want to be the resulting image. The coordinates of these points are given in the picked points side bar. _Minimum of 2 points are required_. 
Parameters: None
#### Perfect Lattice
Select 2 Bragg peaks on the Fourier transform of the image using the picked points. The second point selected must be clockwise and adjacent to the first. Set them as Bragg peaks using the [[#Set Bragg Peaks]] function. 
Select the either of the below functions depending on the crystal symmetry you are analyzing. 
[[#Padding]] is usually added to the image. You must [[#Crop Region]] to be able to view the original image area easily
##### Square
Select this function if your data is a square lattice, e.g. YBCO
Parameters: None
##### Hexagonal
Select this function if your data is a square lattice, e.g. NbSe2
Parameters: None
#### Lawler-Fujita Correction
Select any 2 Bragg peaks on the [[#Auxiliary]] canvas which show the Fourier transform of the [[#Main]] image use the [[#Set Bragg Peaks]] function. 
Input the $\sigma_{ref_{a_0}}$ into the parameter box. This is the variance for the Gaussian window in Real-Space using the lattice constant $r$ as reference. 
Select Lawler-Fujita Correction.
[[#Padding]] is usually added to the image. You must [[#Crop Region]] to be able to view the original image area easily.
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters:
-  $\sigma_{ref_{a_0}}$: float
	- Specify the variance used for the Gaussian Window. This is in units of the lattice constant, $a_0$ which is automatically calculated. 
	- *Default: 10 $\times$ $a_0$ 

#### Line Cut
For a multi-layer dataset array[z,y,x], a straight line is defined by two user-selected Line Cut points in the image plane. For each layer z, the data values are sampled along this line, producing one 1D trace per layer. All such per-layer traces are then stacked together to form a 2D array
Select two points for the line cut on the [[#Main]] canvas. Set them as Line cut points using [[#Set Line Cut Points]]. 
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters:
- Order: int
	- interpolation/sampling method along the cut
		•	0 → nearest
		•	1 → bilinear (default)
		•	2 → biquadratic
		•	3 → bicubic
		•	else → Bresenham (discrete pixels; no interpolation)
	- *Default: 1*
- line_width: int
	- perpendicular averaging width (in pixels)
		•	1 means pure 1-pixel thin line
		•	>1 means for each along-line point, take W points in the normal direction and average
	- *Default: 0*
- num_points: int
	- number of sample points along the cut; controls the sampling density along the line.
	- *Default: the integer length of the line segment between the two selected points, measured in pixels.*
Then select one of the following functions. 
##### A(r)
When option A(r) is selected, the linecut is represented as a function of the distance r measured from the first selected point along the chosen line.
The horizontal axis is the distance r, and the vertical axis is the sampled intensity.
One curve is produced per layer of the 3D dataset; thus the total number of curves equals the number of layers.
The result is stored as a uds2D variable, which must be sent from the local variable list of Image2U3 back to the global variable list, and then forwarded to Plot1U2 for visualization.
In the final plot, all curves are displayed in a single figure with a fixed vertical offset between layers for clarity.
##### A(E)
When option A(E) is selected, the linecut is represented as a function of energy, where each layer corresponds to one energy value.
The horizontal axis is the layer energy, and the vertical axis is the sampled intensity at each spatial point along the line.
One curve is produced per sampling point along the line; thus the total number of curves equals num_points.
The result is stored as a uds2D variable and must be sent from the local variable list of Image2U3 back to the global variable list, then forwarded to Plot1U2 for visualization.
In the final plot, all curves (corresponding to different spatial positions) are displayed in one figure with a constant vertical offset.
##### E VS r
When option A(E vs r) is selected, the linecut result is displayed directly as a 2D image (imshow style). An empty singleton dimension is automatically added, promoting the result to a uds3D variable, so that it can be shown directly in the Image2U3 module without being sent to other modules. In this representation, the horizontal axis corresponds to the distance r along the linecut, and the vertical axis corresponds to the energy associated with each layer. The total number of pixels in the resulting image is num_points × number of layers.
#### Circle Cut 
For a multi-layer dataset data3D[z,y,x], a circle is defined by two user-selected points: the first Cirlce Cut point is taken as the center, and the distance between the two points defines the radius.
For each layer z, values are sampled along this circle, producing one 1D trace per layer.All such layer-wise traces are then stacked into a 2D array.
Select two points for the circle cut on the [[#Main]] canvas. Set them as Circle Cut points using [[#Set Circle Cut Points]]. 
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters:
- Order: int
	- interpolation/sampling method along the cut
		•	0 → nearest
		•	1 → bilinear (default)
		•	2 → biquadratic
		•	3 → bicubic
	- *Default: 1*
- line_width: int
	- perpendicular averaging width (in pixels)
		•	1 means pure 1-pixel thin line
		•	>1 means for each along-line point, take W points in the normal direction and average
	- *Default: 0*
- num_points: int
	- number of sample points along the cut; controls the sampling density along the line.
	- *Default: circumference (≈ int($2πR$) in pixels)*
Then select the following functions. 
##### E VS Theta
At present, Circle Cut supports only the E vs θ representation — typically used for FFT data.
When option E vs θ is selected, the circle cut is represented as a function of angle θ. The angle θ is defined from the circle center, with θ=0 aligned to the second selected Circle Cut point.
The computed result is displayed directly as a 2D image (imshow style). An empty singleton dimension is automatically added, promoting the result to a uds3D variable, so that it can be shown directly in the Image2U3 module without being sent to other modules.
In this representation, the horizontal axis corresponds to the angle θ (num_points samples), and the vertical axis corresponds to the energy associated with each layer (number_of_layers). The total number of pixels in the resulting image is: num_points × number_of_layers.
#### Register
To register 2 images together, you must first select the image to be registered in the [[#Main]] section and the reference image in the [[#Auxiliary]] section. 
Then you must mark 3 registration points in the both images and set them as [[#Register Points]] and [[#Register Reference Points]] in the [[#Points Menu]]
Then you can click Register. 
*Tip*: the settings in the preference can be changed to make sync the cursor in both Main and Auxiliary in the [[#Preferences]] under [[#Main & Auxiliary]]. 
Parameters: None
#### Fourier Filter
This does a 2D gaussian filter on the FFT about the points that you choose.
Select this point on the Auxiliary FFT to be the center of the 2D impulse. Set the point using [[#Set Filter Points]].
Parameters may be entered before choosing the function. Leaving it empty uses the default value. 
Parameters:
-   $k_{\sigma}$: float
	-  The number of of pixels to be blurred out. 
	- *Default: 1.0* 
The choose from one of the following: 
##### Filter Out
This will filter out the points affected by the gaussian filter on the FFT in the Auxiliary and generate a image based on that Fourier transform in Main.
##### Isolate
This will isolate the points affected by the gaussian filter on the FFT in the Auxiliary and generate a image based on that Fourier transform in Main.
#### Math
These are all basic mathematical functions 
##### m+s
This adds the Auxiliary image to the Main image by adding the values at each point together. 
Parameters: None
##### m-s
This subtracts the Auxiliary image from the Main image by subtracting the values at each point from each other. 
Parameters: None
##### m\*const.
This multiplies the Main image by a constant.
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
- const: float
	- Specifies the constant.
	- *Default: 1*
##### m/s
This divides the Main image by the Auxiliary image point by point. 
Parameters: None
##### m/const.
This divides the Main image by a constant. 
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
- const: float
	- Specifies the constant.
	- *Default: 1*
##### const./m
This divides a constant by the Main image. 
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
- const: float
	- Specifies the constant.
	- *Default: 1*
##### Integral
This function preforms an integral over the layers in the 3D data set in Main.
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters: 
- start: int
	- Specifies the starting layer.
	- *Default: 0*
- end: int
	- Specifies the end layer.
	- *Default: n where n is the maximum number of layers*
##### Normalization
For each layer, every data point is normalized by dividing it by the total sum of all values in that layer.
Parameters: None
#### Extract one Layer
For 3D data files, only 2D data can be displayed at once in the module. This extracts one layer as a separate data files for manipulation. 
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
- Layer index: int
	- Specifies layer to be extracted.
	- *Default: 0*
#### Padding
Padding is required to add more data to the edges of the 2D data set. The added pixels span the length or width of the image. 
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters: 
- px: int
	- The number of pixels added to the bottom of the image
	- *Default: 0*
- py: int
	- The number of pixels added to the left side of the image
	- *Default: 0*
- nx: int
	- The number of pixels added to the top of the image
	- *Default: 0*
- ny: int
	- The number of pixels added to the right side of the image
	- *Default: 0*
- a: float
	- The padding constant 
	- *Default: 0*

This is also used by many other functions and if the data added is far outside the 5 sigma range, it will need to be cropped for you to see the original image. You can crop using [[#Crop Region]]
#### Interpolation
Interpolate each layer of the 3D data with structured 2x upsampling
Parameters: None
#### N-fold Symmetrize
This function symmetrizes the data about the center point of the image in Main, usually used for _fft data.  
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
- N: int
	- Specifies the number of symmetries that you want to symmetrize your data to.
	- *Default: 6*
#### Customized Algorithm
This is where a customize algorithm would be displayed. 
### Analysis Menu
#### Fourier Transform
This performs a 2D Fast Fourier transform on the Main image. This is automatically done when a main dataset is selected and is shown in the slave dataset. 
Parameters: None
#### 2D Lock-in
This is used to extract the local amplitude and phase information at a specific momentum point.
First set the Bragg peaks using [[#Set Bragg Peaks]] on the Auxiliary image.
Then you need to set the points of the specific frequency you wish to analyse as the Lock-in points using [[#Set 2D Lock-In Points]]. 
You then select your $\sigma_{ref_{a_0}}$ and type that into the parameters box. 
Then you use the 2D lock in function and select either of the follow map functions. 
Parameters may be entered before choosing the function. Leaving it empty uses the default value.
Parameters: 
-  $\sigma_{ref_{a_0}}$ : float
	- Specifies the size of the Gaussian window used for 2D lock-in in real space, measured in units of the lattice constant $a_0$
	- *Default: 1.0*
##### Amplitude Map
This provides the amplitude maps for the 2D Lock-in
##### Phase Map
This provides the phase maps for the 2D Lock-in
#### Gap-map
The gap map performs a polynomial fit to the coherence peak and calculates the bias value at the maximum. 
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters: 
-  order: int
	- order of the polynomial fit
	- *Default: 2* 
- start_index: int
	- starting layer index for the fitting range
	- *Default: 0*
- end_index : int
	- ending layer index for the fitting range
	- *Default: -1*

#### R-Map 
This processes the 3D mapping data by pairing each positive‐energy layer with the corresponding negative‐energy layer of the same absolute value, then dividing the positive‐energy data by the negative‐energy data, thereby producing a 3D dataset with half the original number of layers.
Parameters: None
#### Cross Correlation 
##### Cross Correlation 
This function performs a cross correlation on the Main image with the Auxiliary image
Parameters: None
##### Statistical Cross Correlation
The origin is the point at the bottom left of the image, the horizontal axis represents the intensity of the data in main, and the vertical axis represents the intensity of the data in Auxiliary. It can show the positive or negative correlations between the data in Main and Auxiliary.
Parameters may be entered before choosing a function. Enter them in the order listed below, separated by commas (","). All parameters are optional — leaving them empty uses all defaults; entering only the first few will cause the remaining ones to fall back to their default values.
Parameters: 
- Size: int
	- Defines the linear dimension (in pixels) of the generated square output image (size × size). It also sets the sampling interval in both axes: the range between the minimum and maximum values in Main (x-axis) and in Auxiliary (y-axis) is uniformly resampled into size points along each direction.
	- *Default:100*
- Sigma: float
	- This is the standard deviation
	- *Default:3*

### Points Menu
#### Set Bragg Peaks
Select the Bragg peaks on the Fourier Transform in the Auxiliary Make sure the point are on the strongest value for cleanest results. You can view the value of each point on the data coords box. 
Select Set Bragg Peaks from the points menu. 
Once set, the coordinates will be shown in the Info Box on the Main image.
#### Set Filter Points
Select the Filter point on the Fourier Transform in the Auxiliary. 
Select Set Filter Points from the points menu. 
Once set, the set point will be shown in the Info Box on the Main image.
#### Set 2D Lock-In Points
Select the 2D Lock-In Points on the Fourier Transform in the Auxiliary. Make sure the point are on the strongest value for cleanest results. You can view the value of each point on the data coords box. 
Select Set Bragg Peaks from the points menu. 
Once set, the coordinates will be shown in the Info Box on the Main image.
#### Set Line/Circle Cut Points
This set the points in the Main image that are used in Line. This points are then stored in info section below the image
#### Set Register Points 
##### Register Points
This set the points in the Main image that are used in registration. This points are then stored in info section below the image
##### Register Reference
This set the points in the Auxiliary image that are used in registration. This points are then stored in info section below the image
### Simulate Menu
#### Generate Lattice 
##### Perfect Lattice
This creates a perfect lattice. 
The first atom placed will be at (0,0) and $a_1$ and $a_2$ are the primitive lattice vectors. You can provide an offset to the starting lattice point. 
Each atom is a Gaussian function with a max value of 1 at the center and a spread of 0.2.  
You can set the period of the intensity using p1 and p2. 
Parameters: 
- n: int
	- number of atoms in the x direction starting on the left. 
	- *Default: 20*
- m: int 
	- number of atoms in the y direction starting on the from the top
	- *Default: 20*
- a1x: int
	- Defines the x component of $a_1$ 
	-  *Default: 10*
- a1y: int
	- Defines the y component of $a_1$ 
	- *Default: 0*
- a2x: int
	- Defines the x component of $a_2$ 
	- *Default: 0*
- a2y: int
	- Defines the y component of $a_2$ 
	- *Default: 10* 
- atomSize: int
	- Defines the size of the atom in space. 
	- *Default: (a1+a2)/2*
- atomCurve: string
	- Defines the distribution of the atom and give it the curve in 2D. 
	- This can only be Gaussian currently. 
	- *Default: Gaussian*
- Ox: int
	- x component offset to the starting lattice point
	- *Default: 0*
- Oy: int
	- y component offset to the starting lattice point
	- *Default: 0*
- p1: float
	- This is the period of the intensity of the atoms in the x direction
	- *Default: 1*
- p2: float
	- This is the period of the intensity of the atoms in the y direction
	- *Default: 1*
##### Domain Wall 
This creates a perfect lattice as in [[#Generate Lattice]]. 
The domain wall will be generated at mod$(n/2)+1$. You can specify a shift distance in the function parameters. 
Parameters: 
- n: int
	- number of atoms in the x direction starting on the left. 
	- *Default: 20*
- m: int 
	- number of atoms in the y direction starting on the from the top
	- *Default: 20*
- a1x: int
	- Defines the x component of $a_1$ 
	-  *Default: 10*
- a1y: int
	- Defines the y component of $a_1$ 
	- *Default: 0*
- a2x: int
	- Defines the x component of $a_2$ 
	- *Default: 0*
- a2y: int
	- Defines the y component of $a_2$ 
	- *Default: 10* 
- atomSize: int
	- Defines the size of the atom in space. 
	- *Default: (a1+a2)/2*
- shiftDistance: float
	- Specifies the distance of the shift between the atoms along the domain wall. 
	- Added distance = shiftDistance\*min($a_1+a_2$)
	- *Default: 0.25*
- atomCurve: string
	- Defines the distribution of the atom and give it the curve in 2D. 
	- This can only be Gaussian currently. 
	- *Default: Gaussian*
- Ox: float
	- x component offset to the starting lattice point
	- *Default: 0*
- Oy: float
	- y component offset to the starting lattice point
	- *Default: 0*
##### Periodic Distortions 
This creates a perfect lattice as in [[#Generate Lattice]] except with a periodic distortion. 
The change in the periodic displacement is defined as $\Delta_{a_{1x}} = A_1a_1*\cos(2\pi m (a_{1x}/dx) + \phi)$ 
Parameters: 
- n: int
	- number of atoms in the x direction starting on the left. 
	- *Default: 20*
- m: int 
	- number of atoms in the y direction starting on the from the top
	- *Default: 20*
- a1x: int
	- Defines the x component of $a_1$ 
	-  *Default: 10*
- a1y: int
	- Defines the y component of $a_1$ 
	- *Default: 0*
- a2x: int
	- Defines the x component of $a_2$ 
	- *Default: 0*
- a2y: int
	- Defines the y component of $a_2$ 
	- *Default: 10* 
- d1x: int
	- The amount of change of the $a_1$ vector in the x direction
	- *Default: none - required*
- d1y: int
	- The amount of change of the $a_1$ vector in the y direction
	- *Default: none - required*
- d2x: int
	- The amount of change of the $a_2$ vector in the x direction
	- *Default: none - required*
- d2y: int
	- The amount of change of the $a_1$ vector in the y direction
	- *Default: none - required*
- dpA1:
	- The change in amplitude of the $a_1$ vector
	- *Default: 0.1*
- dpA2: int
	- The change in amplitude of the $a_2$ vector
	- *Default: 0.1*
- atomSize: int
	- Defines the size of the atom in space. 
	- *Default: (a1+a2)/2*
- shiftDistance: float
	- Specifies the distance of the shift between the atoms along the domain wall. 
	- Added distance = shiftDistance\*min($a_1+a_2$)
	- *Default: 0.25*
- atomCurve: string
	- Defines the distribution of the atom and give it the curve in 2D. 
	- This can only be Gaussian currently. 
	- *Default: Gaussian*
- Ox: float
	- x component offset to the starting lattice point
	- *Default: 0*
- Oy: float
	- y component offset to the starting lattice point
	- *Default: 0*
- dPhi1
- dPh2
#### Generate Curve
##### Heaviside 2D
This creates a 2D Heaviside curve with the step edge with a value of 0 on the left side and a value of 1 on the right. 
Parameters: 
- Size: int
	- Defines the linear dimension (in pixels) of the generated square output image (size × size).
	- *Default: none - required*
- edge_x: int
	- Defines the x co-ordinate of the step edge
	- *Default: 0*
- edge_y: int
	- Defines the y co-ordinate of the step edge
	- *Default: 0*
##### Circle 2D
This makes a circle of value 1 in the 2D plane and a value of 0 outside of the circle
Parameters: 
- Size: int
	- The size of the image to be generated 
	- *Default: none - required*
- Radius: int
	- The radius of the circle to be generated
	- *Default: none - required*
- center_x: int
	- The x coordinate for the center of the circle added to the Centre coordinate. 
	- Eg, if the centre is (100,100), putting 50 into the parameter box would give (150,100). 
	- *Default: 0*
- center_y: int
	- The y coordinate for the center of the circle added to the Centre coordinate. 
	- Eg, if the centre is (100,100), putting 50 into the parameter box would give (100,150). 
	- *Default: 0*
##### Gaussian 2D
This makes a Gaussian of value 1 in the 2D plane and a variance of sigma which needs to be specified. 
-  Size: int
	- The size of the image to be generated 
	- *Default: none - required*
- sigma: int
	- The spread of the Gaussian to be generated
	- *Default: none - required*
- center_x: int
	- The x coordinate for the center of the circle added to the Centre coordinate. 
	- Eg, if the centre is (100,100), putting 50 into the parameter box would give (150,100). 
	- *Default: 0*
- center_y: int
	- The y coordinate for the center of the circle added to the Centre coordinate. 
	- Eg, if the centre is (100,100), putting 50 into the parameter box would give (100,150). 
	- *Default: 0*
##### Sinusoidal 2D
	This generates a 2D sinusoidal wave. 
Parameters
- Size: int
	- Size of the image to be generated
	- *Default: none - required*
- qx: 
	- Direction of the $q_x$ vector
	- *Default: none - required*
- qy: 
	- Direction of the $q_y$ vector
	- *Default: none - required*
- phase: 
	- The phase of the wave in radians. 
	- *Default: none - required*
### Widget Menu
These widgets support docking, floating, closing, and restriction of allowable docking orientations.
#### Variable Dock Widget
Adds the [[#Var Dock Widget]] to the left hand side of the module
#### Plot 1D Dock Widget 
Click to open the Plot 1D DockWidget. If this widget does not appear, check the tabs at the bottom of the Variables DockWidget to see whether it is stacked together with the Variables DockWidget.
For multi-layer datasets—for example, differential conductance spectra dI/dV measured at multiple energies—the Plot 1D Dock Widget is used to display energy-resolved spectra at selected spatial locations.
Two push buttons correspond to two interaction modes: Real Time and Select Points. By default, neither mode is active; clicking a button activates the corresponding mode.
- Real Time mode: The widget continuously displays the spectrum at the spatial position currently indicated by the mouse cursor in the MAIN canvas.
- Select Points mode: The widget displays spectra at user-selected spatial points. Spatial points can be selected by left-clicking on the MAIN canvas. The coordinates of the selected points are listed in the box under “Picked Points”. Multiple spatial points can be selected simultaneously, and the corresponding spectra are displayed together for comparison.
### Options Menu
#### Preference
This allows you to change the display options for the following:
##### ColorMap
-  Here you can add, remove and change the order of the color scales. 
- You can then update them instantly to check what they look like.
- You can also add color scales to your clipboard to paste them elsewhere.
##### Main & Auxiliary
 - The sync section allows you to sync the Main and Auxiliary for easy comparison
 - The lock section allows you to lock the scale for either the Main or the Auxiliary
 - The coefficient section allows you to contract the color scale and how it presents. By default sigma is set to 5
##### Canvas
- This allows you to change the size of the canvas as a fraction of the window size. Default is 0.33.
- You can also show the bias value of the data from the meta data 

## Plot1U2 (Multiple 1D Curves Visualizer & Analyzer)
The module displays 1D curves on a 2D graph
The window is split into 3 sections. The Docked Widget on the left, the variable display in the middle and the graph on the right.
### Docked Widget
The left docked widget has two tabs on the bottom left of the screen:
#### Plot Config
##### Figure Configuration
This configures the following elements of the figure
- Width
- Height
- DPI : Dots per inch
- Figure Title
- Face Color: This is the color surrounding the figure. You can input the color in hexadecimal or click the 'c' button. 
- Edge Color: This is the border color. You can input the color in hexadecimal or click the 'c' button. 
- Transparency: Here you can toggle the transparency of the face and edge of the graph. The value must be between 0 and 1. 
- Padding: Here you can remove the padding from the face of the graph. 
##### Axis Configuration
This configures the following elements of the axes
- Axes Title
- X-axis Label
- Y-axis Label
- X-axis min: You can use m,u,n,p,f,a to denote metric prefixes when needed
- X-axis max: You can use m,u,n,p,f,a to denote metric prefixes when needed
- Y-axis min: You can use m,u,n,p,f,a to denote metric prefixes when needed
- Y-axis max: You can use m,u,n,p,f,a to denote metric prefixes when needed
- X-Scale: You can choose between linear and log
- Y-Scale: You can choose between linear and log
##### Line Configuration
This configures the following elements of the one line that is selected in the middle variable display. 
- Line Width
- Line Style
- Line Color
- Marker Style
- Marker Size
- Marker Face Color
- Marker edge width
- Marker Edge color
You can select different lines on the middle variable display and edit them individually. 

#### Var
##### Local Var List
This is a list of the [[#Local Variables]] used by the modules. To view the a Local Variable in the Graph section, double click on the files name. The Var will be automatically shown in the middle Variable Display. 
##### Remove Variable
The "Remove Variable" button will delete the selected variable from the Local Var List. 
When a variable has been deleted, there is no way to restore this variable. 
##### <- Send <-
This sends the selected Local Variable back to the Global variable list. From there they can be saved or sent into a different module.  
##### Process History
This give a chronological list of all processes that have been conducted on this variable.
### Variable Display
This section has the list of variables on currently being shown on the graph. You can expand the variable name to show a list of all the lines associated with that variable. 
You can select all line and unselect all lines, using the respective buttons below. 
You will be able to select the lines you wish to view by selecting the line, and clicking the "Add to plot" button. Similarly, you can use the "Remove from plot" to remove those line from the plot. 
At the bottom is the Params box, which will allow you in input parameters to use in the Process, analysis and simulate menus. 
### Graph Display
The graph display allows you to see the plot as you change it. 
### Widgets
#### Variables DockWidget
This button reopens the Variables DockWidget if it has been closed.
## RtSynthesis2U3 (Data Simulator)
This module allow you to model the waveforms in real space. It is split into 3 sections. The Docked widget on the left, Synthesis in the middle and the Function on the right. The docked widget only holds the Variable widget
### Docked Widget
#### Var
##### Local Var List
This is a list of the [[#Local Variables]] used by the modules. To view the a Local Variable in the Graph section, double click on the files name. The Var will be automatically shown in the middle Variable Display. 
##### Remove Variable
The "Remove Variable" button will delete the selected variable from the Local Var List. 
When a variable has been deleted, there is no way to restore this variable. 
##### <- Send <-
This sends the selected Local Variable back to the Global variable list. From there they can be saved or sent into a different module.  
##### Process History
This give a chronological list of all processes that have been conducted on this variable.
###  Synthesis
This has simplified version of the [[#Main]] layout from the Image2U3 
### Function
You can use this to input the parameters for the function. 
The function is written at the top of the screen as: $$\Sigma (A_j *\cos(Q_j*r - \phi_j)) $$
#### Data size
This allow you to specify the number of pixels, $n$ that is used to make the $n*n$ image. The default is 256
To add a modulation, use the "Add $Q_j$".
To remove a modulation, use the "Remove $Q_j$"
When you are happy with the output, you can use the "Save to Local Var" button to add to your local variable list to use in other modules. 

When a $Q_j$ is added, a new set of parameters are added to the the box below the button. 
Here you can:
- Specify the $q_x$ component of $Q_j$ under qx
- Specify the $q_y$ component of $Q_j$ under qy
- Specify the $A_j$ under Amplitude. The slider default scale starts from 0 to 1 but this can be changed. Use the scale to show in real time, how the modulation evolves as a function of amplitude. 
- Specify the $\phi_j$ component under Phase. The slider default scale starts from -3.14 to 3.14 or from $-\pi$ to $\pi$ but this can be changed also. Use the scale to show in real time, how the modulation evolves as a function of phase. 