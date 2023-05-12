import torch
import torch.nn as nn

from collections import Counter
from architectures.dae_networks import Encoder, Decoder

class DAE(nn.Module):
    def __init__(self, latent_dim, device, exclude_modality, layer_dim=-1, noise_factor=0.3, test=False, verbose=False):
        super(DAE, self).__init__()
        self.layer_dim = layer_dim
        if self.layer_dim == -1:
            if exclude_modality == 'image':
                self.layer_dim = 200
                self.modality_dims = [0, 200]
            elif exclude_modality == 'trajectory':
                self.layer_dim = 28 * 28
                self.modality_dims = [0, 28 * 28]
            else:
                self.layer_dim = 28 * 28 + 200
                self.modality_dims = [0, 28 * 28, 200]

        self.encoder = Encoder(latent_dim, self.layer_dim)
        self.decoder = Decoder(latent_dim, self.layer_dim)

        self.device = device
        self.test = test
        self.noise_factor = noise_factor
        self.verbose = verbose
        self.exclude_modality = exclude_modality

    def set_verbose(self, verbose):
        self.verbose = verbose

    def add_noise(self, x):
        if len(x) == 2:
            img_noisy = x[0] + torch.randn_like(x[0]) * self.noise_factor
            traj_noisy = x[1] + torch.randn_like(x[1]) * self.noise_factor
            x_noisy = [torch.clip(img_noisy, 0., 1.), torch.clip(traj_noisy, 0., 1.)]
        else:
            x_noisy = torch.clip(x, 0., 1.) + torch.rand_like(x) * self.noise_factor
        return x_noisy

    def forward(self, x):
        data_list = list(x.values())
        if len(data_list[0].size()) > 2:
            data = torch.flatten(data_list[0], start_dim=1)
        else:
            data = data_list[0]

        for id in range(1, len(data_list)):
            data = torch.concat((data, data_list[id]), dim=-1)

        z = self.encoder(data)
        tmp = self.decoder(z)

        x_hat = dict.fromkeys(x.keys())
        for id, key in enumerate(x_hat.keys()):
            x_hat[key] = tmp[:, self.modality_dims[id]:self.modality_dims[id]+self.modality_dims[id+1]]
            if key == 'image':
                x_hat[key] = torch.reshape(x_hat[key], (x_hat[key].size(dim=0), 1, 28, 28))

        return x_hat, z
    
    def loss(self, x, x_hat, scales):
        loss_function = nn.MSELoss().cuda(self.device)
        recon_losses =  dict.fromkeys(x.keys())

        for key in x.keys():
            recon_losses[key] = scales[key] * loss_function(x_hat[key], x[key])

        recon_loss = 0
        for value in recon_losses.values():
            recon_loss += value

        loss_dict = Counter({'Total loss': recon_loss, 'Img recon loss': recon_losses['image'], 'Traj recon loss': recon_losses['trajectory']})
        return recon_loss, loss_dict
