from D3PDMakerCoreComps.D3PDObject import D3PDObject
import D3PDMakerCoreComps

from D3PDMakerConfig.D3PDMakerFlags import D3PDMakerFlags
from AthenaPython import PyAthena

from D3PDMakerA4.D3PDMakerA4Conf import D3PD__A4DumpAlg

from AthenaCommon.Logging import logging
from AthenaCommon.AlgSequence import AlgSequence
topSequence = AlgSequence()

##
# A class very similar to D3PDMakerCoreComps.MakerAlg, but it creates a configured
# version of the D3PD::A4DumpAlg. Can be used directly as if it were a MakerAlg
# object.
class A4DumpAlg( D3PD__A4DumpAlg ):

    def __init__( self,
                  name,
                  seq = topSequence,
                  tuplename = None,
                  preD3PDAlgSeqName = D3PDMakerFlags.PreD3PDAlgSeqName(),
                  orig_stream = None,
                  **kwargs ):

        self.__orig_stream = orig_stream
        self.__logger = logging.getLogger( "A4DumpAlg" )

        # Work around initialization order issue.
        seq.__iadd__( D3PDMakerCoreComps.DummyInitAlg( name + 'DummyInit' ),
                      index = 0 )

        # tuple name defaults to the algorithm name.
        if tuplename == None:
            tuplename = name

        # Create the algorithm Configurable.
        D3PD__A4DumpAlg.__init__ ( self, name,
                                        TupleName = tuplename,
                                        **kwargs )

        # Add to the supplied sequence.
        if seq:
            # But first, add a sequence for algorithms that should run
            # before D3PD making, if it's not already there.
            preseq = AlgSequence( preD3PDAlgSeqName )
            if not hasattr( seq, preD3PDAlgSeqName ):
                seq += [ preseq ]

            # We don't want to do filtering in the presequence.
            preseq.StopOverride = True
            # Now set up another sequence for filtering.
            # Unlike the presequence, there should be a unique one of these
            # per algorithm.  We also need to break out an additional
            # sequence to which users can add, and to wrap the whole
            # thing in a sequence to prevent a failed filter
            # decision from stopping other algorithms.
            # Like this:
            #
            #   ALG_FilterAlgorithmsWrap (StopOverride = True)
            #     ALG_FilterAlgorithmsHolder
            #       ALG_FilterAlgorithms
            #       ALG
            #     Dummy alg, to reset filter flag
            suffix = D3PDMakerFlags.FilterAlgSeqSuffix()
            wrap = AlgSequence( name + suffix + 'Wrap',
                                StopOverride = True )
            holder = AlgSequence( name + suffix + 'Holder' )
            self.filterSeq = AlgSequence( name + suffix )
            holder += self.filterSeq
            holder += self
            wrap += holder
            wrap += PyAthena.Alg( name + 'Dummy' )
           
            seq += wrap

        # Create a unique collection getter registry tool for this tree.
        from AthenaCommon.AppMgr import ToolSvc
        self._registry = \
           D3PDMakerCoreComps.CollectionGetterRegistryTool (self.name() +
                                                   '_CollectionGetterRegistry')
        ToolSvc += self._registry

        return

    def __iadd__( self, config ):
        """Add a new IObjFillerTool to a tree."""
        if self.__orig_stream:
            self.__orig_stream.__iadd__(config)

        nchild = len( self )
        if type( config ) != type( [] ):
            config = [ config ]
            
        for c in config:
            
            try:
                self.Tools[c.getName()]
            except IndexError:
                in_tools = False
            else:
                # Skip those which already exist
                in_tools = True

            self.__logger.info("Encountered object of type '{0}'.".format(type(c)))
            try:
                class_name = c.ObjectName
            except AttributeError:
                self.__logger.info("No ObjectName: %s, prefix: %s" % (c, c.Prefix))
                class_name = ""

            self.__logger.info("Adding D3PDObject with name '{0}' '{1}' '{2}'"
                               .format(c.Prefix, class_name, c.getName()))
            
            if in_tools:
                continue
                                          
            self.Tools      += [ c ]
            self.Prefixes   += [ c.Prefix ]
            self.ClassNames += [ class_name ]

        super( A4DumpAlg, self ).__iadd__( config )

        # Rescan all children to set the proper collection getter registry.
        self._setRegistry( self )
        # Don't execute the hooks. They are not needed for the reader generation.

        return self

    def _setRegistry( self, conf ):
        """Scan CONF and all children to set the proper
        collection getter registry for this tree.
        """
       
        if conf.properties().has_key( 'CollectionGetterRegistry' ):
            conf.CollectionGetterRegistry = self._registry
        for c in conf.getAllChildren():
            self._setRegistry( c )

        return
