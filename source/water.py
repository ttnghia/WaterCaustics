from heightfields import Tessendorf, Ripples
from surface import Surface
from caustics import Caustics

from pyglet import *
from pyglet.gl import *

from vector import Vector2, Vector3

import shader

class Ocean():
    def __init__(   self,
                    camera,
                    cubemap=None,
                    scale=1.0,
                    tileSize=128,
                    tilesX=1,
                    tilesZ=1,
                    depth=30.0,
                    waveHeight=3.125e-5,
                    wind=Vector2(64.0,128.0),
                    period=10.0,
                    photonScale=4.0,
                    photonIntensity=2.0):
                    
                    
        if cubemap:
            self.cubemapTexture = cubemap.texture
        else:
            self.cubemapTexture = None
            
        self.wind = wind                    # Ocean wind in X,Z axis
        self.waveHeight = waveHeight        # The phillips spectrum parameter
        self.oceanDepth = depth
        self.period = period                # Period of ocean surface anim
        self.drawSeaSurface = True
        self.drawSeaFloor = True
        self.enableCaustics = True
        self.photonIntensity = photonIntensity
        self.photonScale = photonScale
        
        self.tileSize = tileSize
        self.tilesX = tilesX
        self.tilesZ = tilesZ
        self.length = tileSize              # Ocean length parameter
        self.camera = camera
        self.scale = scale

        self.surfaceShader = shader.openfiles(  'shaders/ocean.vertex',
                                                'shaders/ocean.fragment')
        self.groundShader = shader.openfiles(   'shaders/oceanfloor.vertex',
                                                'shaders/oceanfloor.fragment')

        self.oceanFloorTexture = image.load('images/tiles.png').get_texture() 
        
        
        # Caustic texture
        self.causticTexture = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                            self.tileSize, 
                                                            self.tileSize,
                                                            GL_RGBA)
        
        # Use Tessendorf FFT synthesis to create a convincing ocean surface.
        self.heightfield = Tessendorf(  self.tileSize,
                                        self.waveHeight, 
                                        self.wind,
                                        self.length,
                                        self.period)
                                           
        # The water surface
        self.surface = Surface( self.surfaceShader,
                                self.camera,
                                texture=self.oceanFloorTexture,
                                causticTexture=self.causticTexture,
                                cubemapTexture=self.cubemapTexture,
                                heightfield=self.heightfield,
                                tileSize=self.tileSize, 
                                tilesX=self.tilesX,
                                tilesZ=self.tilesZ,
                                scale=self.scale, 
                                offset=Vector3(0.0,self.oceanDepth,0.0))
                                
        # The caustics engine, uses the water surface to generate a caustic tex                      
        self.caustics = Caustics (  self.camera,
                                    self.surface,
                                    self.oceanDepth,
                                    self.causticTexture,
                                    self.photonScale,
                                    self.photonIntensity,
                                 )
        
        # The sea bed, an undisturbed mesh
        self.ground = Surface( self.groundShader,
                                self.camera,
                                texture=self.oceanFloorTexture,
                                causticTexture=self.causticTexture,
                                heightfield=None,
                                tileSize=1, 
                                tilesX=self.tilesX,
                                tilesZ=self.tilesZ,
                                scale=self.scale * self.tileSize, 
                                offset=Vector3(0.0,0.0,0.0))
                                
    def reloadShaders(self):
        from shader import FragmentShader, ShaderError, ShaderProgram, VertexShader
        
        def read_source(fname):
            f = open(fname)
            try:
                src = f.read()
            finally:
                f.close()
            return src
            
        fsrc = read_source('shaders/ocean.fragment')
        fshader = FragmentShader([fsrc])
        vsrc = read_source('shaders/ocean.vertex')
        vshader = VertexShader([vsrc])

        self.surfaceShader = ShaderProgram(fshader, vshader)
        self.surfaceShader.use()
        
        fsrc = read_source('shaders/oceanfloor.fragment')
        fshader = FragmentShader([fsrc])
        vsrc = read_source('shaders/oceanfloor.vertex')
        vshader = VertexShader([vsrc])

        self.groundShader = ShaderProgram(fshader, vshader)
        self.groundShader.use()

        self.surface.setShader(self.surfaceShader)
        self.ground.setShader(self.groundShader)
        
    def setCausticPhotonIntensity(self, intensity):
        self.photonIntensity = intensity
        self.caustics.photonIntensity = self.photonIntensity
    def setCausticPhotonScale(self, scale):
        self.photonScale = scale
        self.caustics.photonScale = self.photonScale
                                
    def setDepth(self, depth):
        self.oceanDepth = depth
        self.caustics.setDepth(self.oceanDepth)
        self.surface.setDepth(self.oceanDepth)
    
    def resetHeightfield(self):
        '''
        Recreate the heightfield engine with new initial parameters, this is
        required for heightfield engines such as Tessendorf as lookup tables
        are generated upon creation based on input paramters
        '''
        del self.heightfield
        self.heightfield = Tessendorf(  self.tileSize,
                                        self.waveHeight, 
                                        self.wind,
                                        self.length,
                                        self.period)
        self.surface.setHeightfield( self.heightfield)   
        
    def setWind(self, wind):
        self.wind = wind      
        self.resetHeightfield()
    def setWaveHeight(self, waveHeight):
        self.waveHeight = waveHeight                        
        self.resetHeightfield()  

    def draw(self,dt):
        if self.drawSeaSurface:
            self.surface.draw(dt)
        if self.drawSeaFloor:
            if self.enableCaustics:
                self.caustics.update(dt)
            self.ground.draw(dt)
        
class Pool():
    '''
    A shallow pool with concentric ripples on its surface
    '''
    def __init__(   self,
                    camera,
                    scale=1.0,
                    tileSize=128,
                    tilesX=1,
                    tilesZ=1,
                    depth=30.0):
    
        self.depth = depth

        self.tileSize = tileSize
        self.tilesX = tilesX
        self.tilesZ = tilesZ

        self.camera = camera
        self.scale = scale
        
        self.surfaceShader = ShaderProgram.open('shaders/colour_by_height.shader')

        
        # Use the shallow pool ripple surface generator
        self.heightfield = Ripples(self.camera, self.tileSize)
                                           
        # The water surface
        self.surface = Surface( self.surfaceShader,
                                self.camera,
                                texture=None,
                                heightfield=self.heightfield,
                                tileSize=self.tileSize, 
                                tilesX=self.tilesX,
                                tilesZ=self.tilesZ,
                                scale=self.scale, 
                                offset=Vector3(0.0,self.depth,0.0))

    def setDepth(self, depth):
        self.surface.setDepth(self.depth)
    def tap(self, tapPosition):
        self.heightfield.tap(tapPosition)

    def draw(self,dt):
        self.surface.draw(dt)        