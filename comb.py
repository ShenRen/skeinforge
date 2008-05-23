"""
Comb is a script to comb the extrusion hair of a gcode file.

To run comb, install python 2.x on your machine, which is avaliable from http://www.python.org/download/

To use the preferences dialog you'll also need Tkinter, which probably came with the python installation.  If it did not, look for it at:
www.tcl.tk/software/tcltk/

To export a GNU Triangulated Surface file from Art of Illusion, you can use the Export GNU Triangulated Surface script at:
http://members.axion.net/~enrique/Export%20GNU%20Triangulated%20Surface.bsh

To bring it into Art of Illusion, drop it into the folder ArtOfIllusion/Scripts/Tools/.

The GNU Triangulated Surface format is supported by Mesh Viewer, and it is described at:
http://gts.sourceforge.net/reference/gts-surfaces.html#GTS-SURFACE-WRITE

To turn an STL file into filled, combed gcode, first import the file using the STL import plugin in the import submenu of the file menu
of Art of Illusion.  Then from the Scripts submenu in the Tools menu, choose Export GNU Triangulated Surface and select the
imported STL shape.  Then type 'python slice.py' in a shell in the folder which slice & comb are in and when the dialog pops up, set
the parameters and click 'Save Preferences'.  Then type 'python fill.py' in a shell in the folder which fill is in and when the dialog
pops up, set the parameters and click 'Save Preferences'.  Then type 'python comb.py' in a shell and when the dialog pops up,
change the parameters if you wish but the default 'Comb Hair' is fine.  Then click 'Comb', choose the file which you exported in
Export GNU Triangulated Surface and the filled & combed file will be saved with the suffix '_comb'.

To write documentation for this program, open a shell in the comb.py directory, then type 'pydoc -w comb', then open 'comb.html' in
a browser or click on the '?' button in the dialog.  To write documentation for all the python scripts in the directory, type 'pydoc -w ./'.
To use other functions of comb, type 'python' in a shell to run the python interpreter, then type 'import comb' to import this program.

The computation intensive python modules will use psyco if it is available and run about twice as fast.  Psyco is described at:
http://psyco.sourceforge.net/index.html

The psyco download page is:
http://psyco.sourceforge.net/download.html

The following examples comb the files Hollow Square.gcode & Hollow Square.gts.  The examples are run in a terminal in the folder which contains
Hollow Square.gcode, Hollow Square.gts and comb.py.  The comb function will comb if 'Comb Hair' is true, which can be set in the dialog or by changing
the preferences file 'comb.csv' with a text editor or a spreadsheet program set to separate tabs.  The functions combChainFile and
getCombChainGcode check to see if the text has been combed, if not they call the getFillChainGcode in fill.py to fill the text; once they
have the filled text, then they comb.


> pydoc -w comb
wrote comb.html


> python comb.py
This brings up the dialog, after clicking 'Comb', the following is printed:
File Hollow Square.gts is being chain combed.
The combed file is saved as Hollow Square_comb.gcode


>python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import comb
>>> comb.main()
This brings up the comb dialog.


>>> comb.combChainFile()
Hollow Square.gts
File Hollow Square.gts is being chain combed.
The combed file is saved as Hollow Square_comb.gcode


>>> comb.combFile()
File Hollow Square.gcode is being combed.
The combed file is saved as Hollow Square_comb.gcode


>>> comb.getCombGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")


>>> comb.getCombChainGcode("
( GCode generated by May 8, 2008 slice.py )
( Extruder Initialization )
..
many lines of gcode
..
")

"""

from vec3 import Vec3
import cStringIO
import euclidean
import fill
import gcodec
import intercircle
import preferences
import time
import vectorwrite


__author__ = "Enrique Perez (perez_enrique@yahoo.com)"
__date__ = "$Date: 2008/21/04 $"
__license__ = "GPL 3.0"

#later maybe use 2d everywhere in case there is movement across layers
def combChainFile( filename = '' ):
	"""Comb a gcode linear move file.  Chain comb the gcode if it is not already combed.
	Depending on the preferences, either arcPoint, arcRadius, arcSegment, bevel or do nothing.
	If no filename is specified, comb the first unmodified gcode file in this folder."""
	if filename == '':
		unmodified = gcodec.getGNUGcode()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	combPreferences = CombPreferences()
	preferences.readPreferences( combPreferences )
	startTime = time.time()
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being chain combed.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	suffixFilename = filename[ : filename.rfind( '.' ) ] + '_comb.gcode'
	gcodec.writeFileText( suffixFilename, getCombChainGcode( gcodeText, combPreferences ) )
	print( 'The combed file is saved as ' + gcodec.getSummarizedFilename( suffixFilename ) )
	if combPreferences.writeSVG.value:
		vectorwrite.writeVectorFile( suffixFilename )
	print( 'It took ' + str( int( round( time.time() - startTime ) ) ) + ' seconds to comb the file.' )

def combFile( filename = '' ):
	"""Comb a gcode linear move file.  Depending on the preferences, either arcPoint, arcRadius, arcSegment, bevel or do nothing.
	If no filename is specified, comb the first unmodified gcode file in this folder."""
	if filename == '':
		unmodified = gcodec.getUnmodifiedGCodeFiles()
		if len( unmodified ) == 0:
			print( "There are no unmodified gcode files in this folder." )
			return
		filename = unmodified[ 0 ]
	combPreferences = CombPreferences()
	preferences.readPreferences( combPreferences )
	if not combPreferences.comb.value:
		print( 'The preference is to not comb, so nothing will be done.' )
		return
	print( 'File ' + gcodec.getSummarizedFilename( filename ) + ' is being combed.' )
	gcodeText = gcodec.getFileText( filename )
	if gcodeText == '':
		return
	suffixFilename = filename[ : filename.rfind( '.' ) ] + '_comb.gcode'
	gcodec.writeFileText( suffixFilename, getCombGcode( gcodeText, combPreferences ) )
	print( 'The combed file is saved as ' + suffixFilename )
	if combPreferences.writeSVG.value:
		vectorwrite.writeVectorFile( suffixFilename )

def getCombChainGcode( gcodeText, combPreferences = None ):
	"Comb a gcode linear move text.  Chain comb the gcode if it is not already combed."
	if not gcodec.isProcedureDone( gcodeText, 'fill' ):
		gcodeText = fill.getFillChainGcode( gcodeText )
	return getCombGcode( gcodeText, combPreferences )

def getCombGcode( gcodeText, combPreferences = None ):
	"Comb a gcode linear move text."
	if gcodeText == '':
		return ''
	if gcodec.isProcedureDone( gcodeText, 'comb' ):
		return gcodeText
	if combPreferences == None:
		combPreferences = CombPreferences()
		preferences.readPreferences( combPreferences )
	if not combPreferences.comb.value:
		return gcodeText
	skein = CombSkein()
	skein.parseGcode( gcodeText )
	return skein.output.getvalue()

def isLoopNumberEqual( betweenX, betweenXIndex, loopNumber ):
	"Determine if the loop number is equal."
	if betweenXIndex >= len( betweenX ):
		return False
	return betweenX[ betweenXIndex ].imag == loopNumber

class CombSkein:
	"A class to comb a skein of extrusions."
	def __init__( self ):
		self.betweens = []
		self.extruderActive = False
		self.halfExtrusionWidth = 0.2
		self.fillInset = 1.9 * self.halfExtrusionWidth
		self.isLoop = False
		self.layer = None
		self.layers = []
		self.lineIndex = 0
		self.lines = None
		self.loop = None
		self.oldLocation = None
		self.output = cStringIO.StringIO()
		self.pointTable = {}

	def addGcodeMovement( self, point ):
		"Add a movement to the output."
		self.addLine( "G1 X" + euclidean.getRoundedToThreePlaces( point.x ) + " Y" + euclidean.getRoundedToThreePlaces( point.y ) + " Z" + euclidean.getRoundedToThreePlaces( point.z ) )

	def addIfTravel( self, splitLine ):
		"Add travel move around loops if this the extruder is off."
		location = gcodec.getLocationFromSplitLine( self.oldLocation, splitLine )
		if not self.extruderActive and self.oldLocation != None:
			self.insertPathsBetween( self.getOutloopLocation( location ), self.getOutloopLocation( self.oldLocation ) )
		self.oldLocation = location

	def getOutloopLocation( self, point ):
		"Add travel move around loops if this the extruder is off."
		if str( point ) not in self.pointTable:
			return point
		closestBetween = None
		closestDistanceSquaredIndex = complex( 999999999999999999.0, - 1 )
		for between in self.betweens:
			distanceSquaredIndex = euclidean.getNearestDistanceSquaredIndex( point, between )
			if distanceSquaredIndex.real < closestDistanceSquaredIndex.real:
				closestBetween = between
				closestDistanceSquaredIndex = distanceSquaredIndex
		if closestBetween == None:
			print( 'This should never happen, closestBetween should always exist.' )
			return point
		closestIndex = int( round( closestDistanceSquaredIndex.imag ) )
		segmentBegin = closestBetween[ closestIndex ]
		segmentEnd = closestBetween[ ( closestIndex + 1 ) % len( closestBetween ) ]
		nearestPoint = euclidean.getNearestPointOnSegment( segmentBegin, segmentEnd, point )
		distanceToNearestPoint = point.distance( nearestPoint )
		nearestMinusOld = nearestPoint.minus( point )
		nearestMinusOld.scale( 1.5 )
		return point.plus( nearestMinusOld )

	def addLine( self, line ):
		"Add a line of text and a newline to the output."
		self.output.write( line + "\n" )

	def addPathBetween( self, betweenFirst, betweenSecond, loopFirst ):
		"Add a path between the perimeter and the fill."
		clockwisePath = []
		widdershinsPath = []
		clockwisePath.append( betweenFirst )
		widdershinsPath.append( betweenFirst )
		nearestFirstDistanceIndex = euclidean.getNearestDistanceSquaredIndex( betweenFirst, loopFirst )
		nearestSecondDistanceIndex = euclidean.getNearestDistanceSquaredIndex( betweenSecond, loopFirst )
		firstBeginIndex = ( int( nearestFirstDistanceIndex.imag ) + 1 ) % len( loopFirst )
		secondBeginIndex = ( int( nearestSecondDistanceIndex.imag ) + 1 ) % len( loopFirst )
		widdershinsLoop = euclidean.getAroundLoop( firstBeginIndex, secondBeginIndex, loopFirst )
		widdershinsPath += widdershinsLoop
		clockwiseLoop = euclidean.getAroundLoop( secondBeginIndex, firstBeginIndex, loopFirst )
		clockwiseLoop.reverse()
		clockwisePath += clockwiseLoop
		clockwisePath.append( betweenSecond )
		widdershinsPath.append( betweenSecond )
		if euclidean.getPathLength( widdershinsPath ) > euclidean.getPathLength( clockwisePath ):
			widdershinsPath = clockwisePath
		for point in widdershinsPath:
			self.addGcodeMovement( point )

	def addToLoop( self, location ):
		"Add a location to loop."
		if self.oldLocation == None:
			return
		if self.layer == None:
			self.layer = []
			self.layers.append( self.layer )
		if self.loop == None and self.isLoop:
			self.loop = [] #starting with an empty array because a closed loop does not have to restate its beginning
			self.layer.append( self.loop )
		self.isLoop = False
		if self.loop != None:
			self.loop.append( location )
			self.pointTable[ str( location ) ] = True

	def insertPathsBetween( self, nextBeginning, pathEnd ):
		"Insert paths between the perimeter and the fill."
		betweenX = []
		switchX = []
		segment = nextBeginning.minus( pathEnd )
		segment.normalize()
		segmentXY = segment.dropAxis( 2 )
		segmentYMirror = complex( segment.x, - segment.y )
		pathEndRotated = euclidean.getRoundZAxisByPlaneAngle( segmentYMirror, pathEnd )
		nextBeginningRotated = euclidean.getRoundZAxisByPlaneAngle( segmentYMirror, nextBeginning )
		y = pathEndRotated.y
		z = pathEndRotated.z
		for betweenIndex in range( len( self.betweens ) ):
			between = self.betweens[ betweenIndex ]
			betweenRotated = euclidean.getPathRoundZAxisByPlaneAngle( segmentYMirror, between )
			euclidean.addXIntersections( betweenRotated, betweenIndex, switchX, y )
		switchX.sort( euclidean.compareSolidXByX )
		maximumX = max( pathEndRotated.x, nextBeginningRotated.x )
		minimumX = min( pathEndRotated.x, nextBeginningRotated.x )
		for xIntersection in switchX:
			if xIntersection.real > minimumX and xIntersection.real < maximumX:
				betweenX.append( xIntersection )
		betweenXIndex = 0
		while betweenXIndex < len( betweenX ) - 1:
			betweenXFirst = betweenX[ betweenXIndex ]
			betweenXSecond = betweenX[ betweenXIndex + 1 ]
			if betweenXSecond.imag == betweenXFirst.imag:
				betweenXIndex += 1
				betweenFirst = euclidean.getRoundZAxisByPlaneAngle( segmentXY, Vec3( betweenXFirst.real, y, z ) )
				betweenSecond = euclidean.getRoundZAxisByPlaneAngle( segmentXY, Vec3( betweenXSecond.real, y, z ) )
				loopFirst = self.betweens[ int( betweenXFirst.imag ) ]
				self.addPathBetween( betweenFirst, betweenSecond, loopFirst )
			betweenXIndex += 1

	def linearMove( self, splitLine ):
		"Add a linear move to the loop."
		location = gcodec.getLocationFromSplitLine( self.oldLocation, splitLine )
		if self.extruderActive:
			self.addToLoop( location )
		self.oldLocation = location

	def parseGcode( self, gcodeText ):
		"Parse gcode text and store the comb gcode."
		self.lines = gcodec.getTextLines( gcodeText )
		for line in self.lines:
			self.parseLine( line )
		self.layerIndex = - 1
		for lineIndex in range( len( self.lines ) ):
			line = self.lines[ lineIndex ]
			self.parseAddTravel( line )

	def parseLine( self, line ):
		"Parse a gcode line."
		self.shouldAddLine = True
		splitLine = line.split( ' ' )
		if len( splitLine ) < 1:
			return 0
		firstWord = splitLine[ 0 ]
		if firstWord == 'G1':
			self.linearMove( splitLine )
		if firstWord == 'M101':
			self.extruderActive = True
		if firstWord == 'M103':
			self.extruderActive = False
			self.loop = None
		elif firstWord == 'M109':
			self.halfExtrusionWidth = 0.5 * gcodec.getDoubleAfterFirstLetter( splitLine[ 1 ] )
		elif firstWord == 'M113':
			self.layer = None
			self.loop = None
			self.oldLocation = None
		elif firstWord == 'M114':
			if len( splitLine ) > 1:
				if splitLine[ 1 ][ 1 : ] == 'edge':
					self.isLoop = True
		elif firstWord == 'M115':
			self.fillInset = gcodec.getDoubleAfterFirstLetter( splitLine[ 1 ] )

	def parseAddTravel( self, line ):
		"Parse a gcode line and add it to the comb skein."
		splitLine = line.split( ' ' )
		if len( splitLine ) < 1:
			return
		firstWord = splitLine[ 0 ]
		if firstWord == 'G1':
			self.addIfTravel( splitLine )
		elif firstWord == 'M101':
			self.extruderActive = True
		elif firstWord == 'M103':
			self.extruderActive = False
		elif firstWord == 'M112':
			self.addLine( 'M111 (comb)' )
		elif firstWord == 'M113':
			self.setBetweens()
		self.addLine( line )

	def setBetweens( self ):
		"Set betweens for the layer."
		halfFillInset = 0.5 * self.fillInset
		self.layerIndex += 1
		self.betweens = []
		for loop in self.layers[ self.layerIndex ]:
			centers = intercircle.getCentersfromLoopDirection( euclidean.isWiddershins( loop ), loop, self.fillInset )
			for center in centers:
				inset = intercircle.getInsetFromClockwiseLoop( center, halfFillInset )
				if euclidean.isWiddershins( center ) == euclidean.isWiddershins( inset ):
					if euclidean.getMaximumSpan( inset ) > self.fillInset:
						self.betweens.append( inset )


class CombPreferences:
	"A class to handle the comb preferences."
	def __init__( self ):
		"Set the default preferences, execute title & preferences filename."
		#Set the default preferences.
		self.comb = preferences.BooleanPreference().getFromValue( 'Comb Hair:', True )
		self.writeSVG = preferences.BooleanPreference().getFromValue( 'Write Scalable Vector Graphics:', True )
		directoryRadio = []
		self.directoryPreference = preferences.RadioLabel().getFromRadioLabel( 'Comb All Unmodified Files in a Directory', 'File or Directory Choice:', directoryRadio, False )
		self.filePreference = preferences.Radio().getFromRadio( 'Comb File', directoryRadio, True )
		self.filenameInput = preferences.Filename().getFromFilename( [ ( 'GNU Triangulated Surface text files', '*.gts' ), ( 'Gcode text files', '*.gcode' ) ], 'Open File to be Combed', '' )
		#Create the archive, title of the execute button, title of the dialog & preferences filename.
		self.archive = [ self.comb, self.writeSVG, self.directoryPreference, self.filePreference, self.filenameInput ]
		self.executeTitle = 'Comb'
#		self.filename = getPreferencesFilePath( 'comb.csv' )
		self.filenamePreferences = 'comb.csv'
		self.filenameHelp = 'comb.html'
		self.title = 'Comb Preferences'

	def execute( self ):
		"Comb button has been clicked."
		filenames = gcodec.getGcodeDirectoryOrFile( self.directoryPreference.value, self.filenameInput.value, self.filenameInput.wasCancelled )
		for filename in filenames:
			combChainFile( filename )


def main( hashtable = None ):
	"Display the comb dialog."
	preferences.displayDialog( CombPreferences() )

if __name__ == "__main__":
	main()