
AngstromPro is a program that allows the use to perform data analysis and image processing on various forms of STM data. The paper related to this program can be found at www.doi:.... This paper gives more details on the mathematics behind the 
 
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
	- The file types that can be uploaded are .uds, .3ds, .sxm, .dat, .tfr, .1fl, .2fl, .ffl, .lfr, .txt. All files uploaded will be then separated into the different channels depending on the type of data uploaded
- Save to file:
	- Save the file currently selected in USD Variables. This will then launch windows explorer to allow you to save in a specific folder and change the file name.

To rename a file in USD Variables, (This breaks actually)

To delete a variable from the USD variables list, you must click the lock/unlock button beneath the USD variable list. This will then activate the “Remove Var” button. You can then select the variable you list to want to remove and select the “Remove Var” button and the variable will be removed from the list. 
## Edit: 
This is currently blank. #unfinished 

## Window: 
This allows you to add a new module in the Alive Modules section. 
	The list of modules includes
		[[#Data Browser]]
		[[#Image2or3D]]
		Plot1U2
		RtSynthesis2
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
### Docked widget: 
This widget has two tabs on the bottom left
#### Channels:
- View: This allows you to choose to see 2 or 3 plots in a row. 
- Channel Filter: Most STM data has multiple different types of data and you can select which type you want to view in the gallery. 
#### Files:
- Data Path: This allows you to set the data path to allow browsing easier. Clicking on the folder populates the gallery with snapshots of files matching the format filter.
- Format Filter: This filers the files in the data to allow you to only see relevant files. You must write the file type as * . ---
### Gallery:  
Here you can see a snapshot of all files in a gallery. Additional blocks provide basic file information and interactive options, such as sending corresponding data to the Global Variable List for further processing.
 - To optimize memory usage, only snapshots currently in view are loaded, while out-of-view snapshots are dynamically discarded. With these features, the Data Browser provides powerful and intuitive tool for efficiently browsing, organizing and exploring enormous and diverse datasets.
## Image2U3
Multiple 2D Images Visualizer & Analyzer module. When opened you are immediately shown an empty Var Dock Widget on the left, and two blank [[#Main]] and [[#Auxiliary]] images.  
### Var Dock Widget
#### Local Var List
This is a list of the [[#Local Variables]] used by the modules. To view the a Local Variable in the Main section, double click on the files name. The fast Fourier transform will be automatically generated in the Auxiliary. 
##### Prefixes
- It will get the prefix "m" if this current local variable is being viewed by the [[Main]] section
- It will get the prefix "s" if this current local variable is being viewed by the [[Auxiliary]] section
- It will get the prefix "ms" if this current local variable is being viewed by both the [[Main]] section and the [[Auxiliary]] section
##### Suffixes
Suffixes are added as new processes are conducted on each variable #unfinished 

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
#unfinished 
#### Image
#### Color Scale
#### Palette
#### Picked Points
#### Params
#### Information

### Auxiliary
#unfinished 
### File Menu
#### Export
This exports either the Main or Auxiliary as a PNG image to be saved locally or be copied to the clipboard.  
#### Make Movie From
Multi-dimensional data can also be exported as an .mp4 files with each layer serving as a frame. 
### Process Menu
#### Background Subtract
This process can help remove a slope from the image that is caused by the angle of the sample relative to the tip of the STM. This will leave behind only the atomic resolution. All backgrounds are calculated using least square fitting. 
##### 2D subtraction
This fits a first order 2D plane to the image and subtract that plane from the image. The fitting is of first order by default
##### Line-By-Line Subtraction
This fits a curve to each horizonal line of the image and subtracts that from the image. The fitting is of first order by default
#### Crop Region
Select 2 points by right clicking on the Main image. These points should be the top left and bottom right corners of the what you want to be the resulting image. The coordinates of these points are given in the picked points side bar. _Minimum of 2 points are required_. 
#### Perfect Lattice
Select 2 Bragg peaks on the Fourier transform of the image using the picked points. The second point selected must be clockwise and adjacent to the first. Set them as Bragg peaks using the [[#Set Bragg Peaks]] function. 
Select the either of the below functions depending on the crystal symmetry you are analyzing. 
[[#Padding]] is usually added to the image. You must [[#Crop Region]] to be able to view the original image area easily
##### Square
Select this function if your data is a square lattice, e.g. YBCO
##### Hexagonal
Select this function if your data is a square lattice, e.g. NbSe2
#### Lawler-Fujita Correction
Select 2 Bragg peaks on the Fourier transform of the image using the picked points. The second point selected must be clockwise and adjacent to the first. Set them as Bragg peaks using the [[#Set Bragg Peaks]] function. 
Input the chosen $\sigma_{r_{ref}}$ into the parameter box. You can obtain the  $\sigma_{r_{ref}}$ by conducting a [[#2D Lock-in]] and choosing either amplitude or phase. The $\sigma_{r_{ref}}$ will be in the data given in terms of $a_{0}$.
Select Lawler-Fujita Correction
[[#Padding]] is usually added to the image. You must [[#Crop Region]] to be able to view the original image area easily
#### Line Cut
#unfinished #NeedExplaination

Select the points for the line cut using the picked points. Set them as Line cut points using [[#Set Line Cut Points]]. The line cut is calculated using Bresenham's Line algorithm. 

Then select one of the following functions. 
##### A(r)
##### A(E)

##### E VS r

This can then be viewed in the 
#### Circle Cut
#unfinished  #NeedExplaination Select the points for the circle cut using the picked points. Set them as Line cut points using [[#Set Line Cut Points]]. Then select one of the following functions. 
##### A(r)
##### A(E)
##### E VS Theta

#### Register
To register 2 images together, you must first select the image to be registered in the [[#Main]] section and the reference image in the [[#Auxiliary]] section. 
Then you must mark 3 registration points in the both images and set them as [[#Register Points]] in the [[#Points Menu]]
Then you can click Register. 
#### Fourier Filter
This does a 2D gaussian filter on the FFT about the points that you choose.
Select this point on the Auxiliary FFT to be the center of the 2D impulse. Set the point using [[#Set Filter Points]]. Input the value for $k_sigma$, which means the number of of pixels in k space, and it’s default value is 1.0, in parameters box. The choose from one of the following: 
##### Filter Out
This will filter out the points affected by the gaussian filter on the FFT in the Auxiliary and generate a image based on that Fourier transform in Main
##### Isolate
This will isolate the points affected by the gaussian filter on the FFT in the Auxiliary and generate a image based on that Fourier transform in Main
#### Math
These are all basic mathematical functions 
##### m+s
This adds the Auxiliary image to the Main image by adding the values at each point together. 
##### m-s
This subtracts the Auxiliary image from the Main image by subtracting the values at each point from each other. 
##### m\*const.
This multiplies the Main image by a constant. The constant is imputed into the parameters box before the process is applied. 
##### m/s
This divides the Main image by the Auxiliary image point by point. 
##### m/const.
This divides the Main image by a constant. The constant is imputed into the parameters box before the process is applied. 
##### const./m
This divides a constant by the Main image. The constant is imputed into the parameters box before the process is applied. 
##### Integral
This function preforms an integral over the whole data set in Main
##### Normalization
This normalizes the whole data set in Main. 
#### Extract one Layer
#unfinished 
For 3D data files, only 2D data can be displayed at once in the module. You can extract an individual layer by 
#### Padding
Padding is required to add more data to the edges of the 2D data set.  
To add padding to a data set, you must specify the amount padded in the parameters box, in the following order. px, py, nx, ny, a where: 
- px is the number of pixels added to the bottom, 
- py is the number of pixels added to the left side
- nx is the number of pixels added to the top
- ny is the number of pixels added to the right side
- a is the padding constant 
The added pixels span the length or width of the image. 

This is also used by many other functions and if the data added is far outside the 5 sigma range, it will need to be cropped for you to see the original image. You can crop using [[#Crop Region]]
#### Interpolation
This function does a simple 2D interpolation of the data and can also do it across all layers in 3D data
#### N-fold Symmetrize
This function symmetrizes the data about the centre point of the fouier transform. The default value is 6-fold but to change this you are about the input a different value for N in the parameters box
#### Customized Algorithm

### Analysis Menu
#### Fourier Transform
This performs a 2D Fourier transform on the Main image. This is automatically done when a main dataset is selected and is shown in the slave dataset. 
#### 2D Lock-in
This is used to extract the local amplitude and phase information at a specific momentum point.
First set the Bragg peaks using [[#Set Bragg Peaks]]. Then you need to set the CDW points as the Lock-in points using [[#Set 2D Lock-In Points]]. You then select your $\sigma_{r_{ref}}$ and type that into the parameters box. Note that $\sigma_{r} = \sigma_{r_{ref}} . a_0$ where $a_0$ is the lattice constant. 
Then you use the 2D lock in function and select either of the follow map functions. 
##### Amplitude Map
##### Phase Map
#### Gap-map
#### Cross Correlation 
##### Cross Correlation 
This function performs a cross correlation on the Main image with the Auxiliary image
##### Statistical Cross Correlation

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
##### Perfect Lattice #unfinished 
This creates a perfect square lattice. 
You can entre the following parameters in the order listed to specify 
- n = number of atoms in the x direction starting on the left. 
- m = number of atoms in the y direction starting on the from the top. 
- a1x = 
- a1y =
- a2x =
- a2y =
- Ox=0, 
- Oy=0
##### Domain Wall #unfinished 
This creates a perfect lattice with a domain wall. You can specify a shift distance  
##### Periodic Distortions #unfinished 
#### Generate Curve
##### Heaviside 2D
#unfinished 
##### Circle 2D
This makes a circle of value 1 in the 2D plane
- Size = Size of the image to be generated
- Radius = Radius of the circle 
- ccenter_x: The x coordinate for the center of the circle added to the Centre coordinate. Eg, if the centre is (100,100), putting 50 into the parameter box would give (150,100). 
	- If none is specified, it will choose the center of the image
- center_y: The y coordinate for the center of the circle added to the Centre coordinate. Eg, if the centre is (100,100), putting 50 into the parameter box would give (100,150). 
	- If none is specified, it will choose the center of the image
##### Gaussian 2D
This makes a Gaussian of value 1 in the 2D plane
- Size = Size of the image to be generated
- Sigma = The spread of the Gaussian 
- center_x: The x coordinate for the center of the circle added to the Centre coordinate. Eg, if the centre is (100,100), putting 50 into the parameter box would give (150,100). 
	- If none is specified, it will choose the center of the image
- ccenter_y: The y coordinate for the center of the circle added to the Centre coordinate. Eg, if the centre is (100,100), putting 50 into the parameter box would give (100,150). 
	- If none is specified, it will choose the center of the image
##### Sinusoidal 2D
This generates a 2D sinusoidal wave 
- Size: Size of the image to be generated
- qx: Direction of the $q_x$ vector
- qy: Direction of the $q_y$ vector
- phase: The phase of the wave in radians.  
- amplitude: Amplitude of the wave. Default is 1
### Widget Menu
#### Variable Dock Widget
Adds the [[#Var Dock Widget]] to the left hand side of the module
#### Plot 1D Dock Widget #unfinished 
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
- You can also show the bias value
	


## Multiple 1D Curves Visualizer & Analyzer