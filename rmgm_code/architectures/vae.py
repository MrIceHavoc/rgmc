import torch
import torch.nn as nn
import numpy as np

from tqdm import tqdm
from collections import Counter
from architectures.vae_networks import Encoder, Decoder

class VAE(nn.Module):
    def __init__(self, latent_dim, device, exclude_modality, scales, layer_dim=-1, verbose=False):
        super(VAE, self).__init__()
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
        self.scales = scales
        self.kld = 0.
        self.verbose = verbose
        self.exclude_modality = exclude_modality

    def set_verbose(self, verbose):
        self.verbose = verbose

    def forward(self, x):
        data_list = list(x.values())
        if len(data_list[0].size()) > 2:
            data = torch.flatten(data_list[0], start_dim=1)
        else:
            data = data_list[0]

        for id in range(1, len(data_list)):
            data = torch.concat((data, data_list[id]), dim=-1)

        z = torch.Tensor

        mean, logvar = self.encoder(data)
        std = torch.exp(logvar/2)
    
        # Reparameterization trick
        dist = torch.distributions.Normal(0, 1)
        eps = dist.sample(mean.shape).to(self.device)

        z = mean + std * eps
        tmp = self.decoder(z)
        
        self.kld += - self.scales['KLD beta'] * (1 + logvar - (mean)**2 - (std)**2).sum()

        x_hat = dict.fromkeys(x.keys())
        for id, key in enumerate(x_hat.keys()):
            x_hat[key] = tmp[:, self.modality_dims[id]:self.modality_dims[id]+self.modality_dims[id+1]]
            if key == 'image':
                x_hat[key] = torch.reshape(x_hat[key], (x_hat[key].size(dim=0), 1, 28, 28))

        return x_hat, z
    
    
    def loss(self, x, x_hat):
        loss_function = nn.MSELoss().cuda(self.device)
        recon_losses =  dict.fromkeys(x.keys())

        for key in x.keys():
            recon_losses[key] = self.scales[key] * loss_function(x_hat[key], x[key])

        recon_loss = 0
        for value in recon_losses.values():
            recon_loss += value
        
        self.kld = self.kld / len(list(x.values())[0])
        elbo = self.kld + recon_loss

        loss_dict = Counter({'Total loss': elbo, 'KLD': self.kld, 'Img recon loss': recon_losses['image'], 'Traj recon loss': recon_losses['trajectory']})
        self.kld = 0.
        return elbo, loss_dict
        
