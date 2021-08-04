import oneflow as flow
from ..q_module import QParam, QModule

class QConv2d(QModule):

    def __init__(self, conv_module, qi=True, qo=True, quantization_bit=8, quantization_scheme='symmetric', quantization_formula='google', per_layer_quantization=True):
        super(QConv2d, self).__init__(qi=qi, qo=qo, quantization_bit=quantization_bit, quantization_scheme=quantization_scheme, quantization_formula=quantization_formula, per_layer_quantization=per_layer_quantization)
        self.quantization_bit = quantization_bit
        self.quantization_scheme = quantization_scheme
        self.quantization_formula = quantization_formula
        self.per_layer_quantization = per_layer_quantization
        self.conv_module = conv_module
        self.qw = QParam(quantization_bit=quantization_bit, quantization_scheme=quantization_scheme, quantization_formula=quantization_formula, per_layer_quantization=per_layer_quantization)

    def freeze(self, qi=None, qo=None):
        
        if hasattr(self, 'qi') and qi is not None:
            raise ValueError('qi has been provided in init function.')
        if not hasattr(self, 'qi') and qi is None:
            raise ValueError('qi is not existed, should be provided.')

        if hasattr(self, 'qo') and qo is not None:
            raise ValueError('qo has been provided in init function.')
        if not hasattr(self, 'qo') and qo is None:
            raise ValueError('qo is not existed, should be provided.')

        if qi is not None:
            self.qi = qi
        if qo is not None:
            self.qo = qo
        self.M = self.qw.scale * self.qi.scale / self.qo.scale

        self.conv_module.weight.data = self.qw.quantize_tensor(self.conv_module.weight.data)
        self.conv_module.weight.data = self.conv_module.weight.data - self.qw.zero_point

        self.conv_module.bias.data = flow.quantization.fake_quantization(self.conv_module.bias.data, scale=self.qi.scale * self.qw.scale,
                                                     zero_point=0, quantization_formula="google", quantization_bit=32, quantization_scheme="affine")

    def forward(self, x):
        if hasattr(self, 'qi'):
            self.qi.update(x)
            x = self.qi.fake_quantize_tensor(x)

        self.qw.update(self.conv_module.weight.data)

        x = flow.F.conv2d(x, self.qw.fake_quantize_tensor(self.conv_module.weight), self.conv_module.bias, 
                     stride=self.conv_module.stride,
                     padding=self.conv_module.padding, dilation=self.conv_module.dilation, 
                     groups=self.conv_module.groups)

        if hasattr(self, 'qo'):
            self.qo.update(x)
            x = self.qo.fake_quantize_tensor(x)

        return x

